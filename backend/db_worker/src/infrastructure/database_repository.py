import json
import os
import pymysql
import threading
import time


class DatabaseRepository:
    """
    외부 MySQL 데이터베이스(faictory_mes)와 통신하여 로봇 실시간 상태,
    완료 결과, Page3 점검 데이터, PLC 이벤트를 저장합니다.

    현장 DB는 payload JSON 중심 스키마를 사용하고, 기존 개발 DB는 컬럼 펼침
    스키마를 사용할 수 있어서 테이블 컬럼을 확인한 뒤 맞는 INSERT를 선택합니다.
    """

    DB_CONFIG = {
        "host": os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "192.168.3.141")),
        "port": int(os.getenv("DB_PORT", os.getenv("MYSQL_PORT", "3306"))),
        "user": os.getenv("DB_USER", os.getenv("MYSQL_USER", "guest")),
        "password": os.getenv("DB_PASS", os.getenv("MYSQL_PASSWORD", "guest1234")),
        "db": os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "faictory_mes")),
        "charset": "utf8mb4",
        "autocommit": True,
        "use_unicode": True,
        "connect_timeout": 5,
        "init_command": "SET NAMES utf8mb4",
    }

    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._columns_cache = {}
        self._operational_tables_ready = False
        self._virtual_tables_ready = False
        self._plc_event_table_ready = False
        self._result_table_ready = False

    def _get_persistent_connection(self):
        """단일 persistent 커넥션을 유지하며, 끊기면 자동 재연결합니다."""
        with self._lock:
            if self._conn is None:
                try:
                    self._conn = pymysql.connect(**self.DB_CONFIG)
                except Exception as exc:
                    print(f">> [DB 에러] 연결 실패: {exc}")
                    return None
            else:
                try:
                    self._conn.ping(reconnect=True)
                except Exception as exc:
                    print(f">> [DB 에러] ping 실패 재연결 중: {exc}")
                    try:
                        self._conn = pymysql.connect(**self.DB_CONFIG)
                        self._columns_cache.clear()
                    except Exception as reconnect_error:
                        print(f">> [DB 에러] 재연결 실패: {reconnect_error}")
                        return None
            return self._conn

    @staticmethod
    def _json(payload):
        return json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _six(values):
        result = list(values or [])[:6]
        while len(result) < 6:
            result.append(0.0)
        return [float(value or 0.0) for value in result]

    @staticmethod
    def _status_label(status_data):
        status = status_data.get("status")
        if isinstance(status, str):
            return status
        if isinstance(status, dict):
            if status.get("emergency"):
                return "emergency"
            if status.get("collision"):
                return "collision"
            if status.get("error"):
                return "error"
            if status.get("busy"):
                return "busy"
            if status.get("ready"):
                return "ready"
        if status_data.get("busy"):
            return "busy"
        return "unknown"

    def _columns(self, table_name):
        cached = self._columns_cache.get(table_name)
        if cached is not None:
            return cached
        conn = self._get_persistent_connection()
        if not conn:
            return set()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                columns = {row[0] for row in cursor.fetchall()}
            self._columns_cache[table_name] = columns
            return columns
        except Exception:
            self._columns_cache[table_name] = set()
            return set()

    def _table_exists(self, table_name):
        conn = self._get_persistent_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    def _ensure_table(self, table_name, create_sql):
        if self._table_exists(table_name):
            return
        conn = self._get_persistent_connection()
        if not conn:
            return
        with conn.cursor() as cursor:
            cursor.execute(create_sql)
        self._columns_cache.pop(table_name, None)

    def _ensure_operational_tables(self):
        if self._operational_tables_ready:
            return
        try:
            self._ensure_table(
                "robot_realtime_status",
                """
                CREATE TABLE IF NOT EXISTS robot_realtime_status (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    robot_id VARCHAR(64),
                    status VARCHAR(64),
                    payload JSON,
                    recorded_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_robot_realtime_time (robot_id, recorded_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._ensure_table(
                "robot_task_history",
                """
                CREATE TABLE IF NOT EXISTS robot_task_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    task_id VARCHAR(96),
                    product_sn VARCHAR(64),
                    status VARCHAR(64),
                    started_at DATETIME(3) NULL,
                    completed_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    details JSON,
                    INDEX idx_task_completed_at (completed_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._operational_tables_ready = True
        except Exception as exc:
            print(f">> [DB 에러] 운영 테이블 준비 실패: {exc}")

    def _ensure_result_table(self):
        if self._result_table_ready:
            return
        try:
            self._ensure_table(
                "robot_result_history",
                """
                CREATE TABLE IF NOT EXISTS robot_result_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    product_sn VARCHAR(64),
                    event_type VARCHAR(64),
                    payload JSON,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._result_table_ready = True
        except Exception as exc:
            print(f">> [DB 에러] 로봇 결과 테이블 준비 실패: {exc}")

    def _ensure_virtual_test_tables(self):
        if self._virtual_tables_ready:
            return
        try:
            self._ensure_table(
                "robot_virtual_test_sessions",
                """
                CREATE TABLE IF NOT EXISTS robot_virtual_test_sessions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(96),
                    started_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    ended_at DATETIME(3) NULL,
                    metadata JSON,
                    INDEX idx_virtual_session_started (started_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._ensure_table(
                "robot_virtual_test_samples",
                """
                CREATE TABLE IF NOT EXISTS robot_virtual_test_samples (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(96),
                    sample_id VARCHAR(96),
                    captured_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    data JSON,
                    INDEX idx_virtual_sample_captured (captured_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._ensure_table(
                "robot_virtual_test_events",
                """
                CREATE TABLE IF NOT EXISTS robot_virtual_test_events (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(96),
                    event_type VARCHAR(64),
                    payload JSON,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_virtual_event_created (created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._virtual_tables_ready = True
        except Exception as exc:
            print(f">> [DB 에러] 로봇 점검 Data수집 테이블 준비 실패: {exc}")

    def _ensure_plc_event_table(self):
        if self._plc_event_table_ready:
            return
        try:
            self._ensure_table(
                "plc_process_events",
                """
                CREATE TABLE IF NOT EXISTS plc_process_events (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    source VARCHAR(128),
                    event_type VARCHAR(64),
                    payload JSON,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_plc_event_created (created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """,
            )
            self._plc_event_table_ready = True
        except Exception as exc:
            print(f">> [DB 에러] PLC 이벤트 테이블 준비 실패: {exc}")

    def insert_realtime_data(self, robot_id: str, status_data: dict):
        """로봇 실시간 상태를 DB에 저장합니다."""
        self._ensure_operational_tables()
        cols = self._columns("robot_realtime_status")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if {"payload", "recorded_at"}.issubset(cols):
                    cursor.execute(
                        """
                        INSERT INTO robot_realtime_status
                          (robot_id, status, payload, recorded_at)
                        VALUES (%s, %s, %s, NOW(3))
                        """,
                        (robot_id, self._status_label(status_data), self._json(status_data)),
                    )
                    return

                q = self._six(status_data.get("q") or status_data.get("joint_pos"))
                tq = self._six(status_data.get("torque"))
                cursor.execute(
                    """
                    INSERT INTO robot_realtime_status
                      (robot_id,
                       j1_deg, j2_deg, j3_deg, j4_deg, j5_deg, j6_deg,
                       t1_nm, t2_nm, t3_nm, t4_nm, t5_nm, t6_nm,
                       updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                      j1_deg=VALUES(j1_deg), j2_deg=VALUES(j2_deg), j3_deg=VALUES(j3_deg),
                      j4_deg=VALUES(j4_deg), j5_deg=VALUES(j5_deg), j6_deg=VALUES(j6_deg),
                      t1_nm=VALUES(t1_nm), t2_nm=VALUES(t2_nm), t3_nm=VALUES(t3_nm),
                      t4_nm=VALUES(t4_nm), t5_nm=VALUES(t5_nm), t6_nm=VALUES(t6_nm),
                      updated_at=NOW()
                    """,
                    (robot_id, *q, *tq),
                )
        except Exception as exc:
            print(f">> [DB 에러] 실시간 상태 저장 실패: {exc}")

    def insert_task_completion(self, robot_id: str, action_type: str, pos: list, payload: dict = None):
        """Pick/Place 등 작업 완료 이력을 DB에 남깁니다."""
        self._ensure_operational_tables()
        cols = self._columns("robot_task_history")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "details" in cols:
                    details = {
                        "robot_id": robot_id,
                        "action_type": action_type,
                        "pos": list(pos or []),
                        "payload": dict(payload or {}),
                    }
                    cursor.execute(
                        """
                        INSERT INTO robot_task_history
                          (task_id, product_sn, status, started_at, completed_at, details)
                        VALUES (%s, %s, %s, NULL, NOW(3), %s)
                        """,
                        (
                            f"{robot_id}_{action_type}_{int(time.time() * 1000)}",
                            "",
                            "completed",
                            self._json(details),
                        ),
                    )
                    return

                p = self._six(pos)
                cursor.execute(
                    """
                    INSERT INTO robot_task_history
                      (robot_id, action_type, pos_x, pos_y, pos_z, completed_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (robot_id, action_type, p[0], p[1], p[2]),
                )
        except Exception as exc:
            print(f">> [DB 에러] {action_type} 이력 저장 실패: {exc}")

    def insert_robot_result(self, payload: dict):
        """robot/result 완료 응답을 DB에 저장합니다."""
        self._ensure_result_table()
        cols = self._columns("robot_result_history")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "payload" in cols:
                    cursor.execute(
                        """
                        INSERT INTO robot_result_history
                          (product_sn, event_type, payload, created_at)
                        VALUES (%s, %s, %s, NOW(3))
                        """,
                        (
                            payload.get("product_sn", ""),
                            payload.get("type", payload.get("event_type", "robot_result")),
                            self._json(payload),
                        ),
                    )
                    return
                print(">> [DB 경고] robot_result_history 테이블이 payload 스키마가 아닙니다.")
        except Exception as exc:
            print(f">> [DB 에러] 로봇 완료 결과 저장 실패: {exc}")

    def insert_plc_process_event(self, payload: dict):
        """PLC master 신호 이벤트를 DB에 저장합니다."""
        self._ensure_plc_event_table()
        cols = self._columns("plc_process_events")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "payload" in cols and "source" in cols:
                    cursor.execute(
                        """
                        INSERT INTO plc_process_events
                          (source, event_type, payload, created_at)
                        VALUES (%s, %s, %s, NOW(3))
                        """,
                        (
                            payload.get("source", payload.get("source_name", "")),
                            payload.get("event_type", payload.get("signal", payload.get("event", "plc_event"))),
                            self._json(payload),
                        ),
                    )
                    return

                cursor.execute(
                    """
                    INSERT INTO plc_process_events
                      (signal_name, station_id, device, edge_name, signal_value,
                       source_name, plc_name, plc_ip, plc_port, description, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload.get("signal", ""),
                        payload.get("station_id", ""),
                        payload.get("device", ""),
                        payload.get("edge", ""),
                        int(payload.get("value", 0) or 0),
                        payload.get("source", ""),
                        payload.get("plc_name", ""),
                        payload.get("plc_ip", ""),
                        int(payload.get("plc_port", 0) or 0),
                        payload.get("description", ""),
                        self._json(payload),
                    ),
                )
        except Exception as exc:
            print(f">> [DB 에러] PLC 이벤트 저장 실패: {exc}")

    def upsert_virtual_test_session(self, payload: dict):
        self._ensure_virtual_test_tables()
        cols = self._columns("robot_virtual_test_sessions")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "metadata" in cols:
                    cursor.execute(
                        """
                        INSERT INTO robot_virtual_test_sessions
                          (session_id, started_at, metadata)
                        VALUES (%s, NOW(3), %s)
                        """,
                        (payload.get("session_id", ""), self._json(payload)),
                    )
                    return

                cursor.execute(
                    """
                    INSERT INTO robot_virtual_test_sessions
                      (session_id, robot_id, program_path, target_cycles, sample_interval_ms, dry_run, status, note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      robot_id=VALUES(robot_id),
                      program_path=VALUES(program_path),
                      target_cycles=VALUES(target_cycles),
                      sample_interval_ms=VALUES(sample_interval_ms),
                      dry_run=VALUES(dry_run),
                      status=VALUES(status),
                      note=VALUES(note)
                    """,
                    (
                        payload.get("session_id", ""),
                        payload.get("robot_id", ""),
                        payload.get("program_path", ""),
                        int(payload.get("target_cycles", 0) or 0),
                        int(payload.get("sample_interval_ms", 100) or 100),
                        1 if payload.get("dry_run", True) else 0,
                        payload.get("status", "running"),
                        payload.get("note", ""),
                    ),
                )
        except Exception as exc:
            print(f">> [DB 에러] 로봇 점검 세션 저장 실패: {exc}")

    def finish_virtual_test_session(self, payload: dict):
        self._ensure_virtual_test_tables()
        cols = self._columns("robot_virtual_test_sessions")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "metadata" in cols:
                    cursor.execute(
                        """
                        UPDATE robot_virtual_test_sessions
                           SET ended_at=NOW(3), metadata=%s
                         WHERE session_id=%s
                         ORDER BY id DESC
                         LIMIT 1
                        """,
                        (self._json(payload), payload.get("session_id", "")),
                    )
                    if cursor.rowcount == 0:
                        cursor.execute(
                            """
                            INSERT INTO robot_virtual_test_sessions
                              (session_id, started_at, ended_at, metadata)
                            VALUES (%s, NOW(3), NOW(3), %s)
                            """,
                            (payload.get("session_id", ""), self._json(payload)),
                        )
                    return

                cursor.execute(
                    """
                    UPDATE robot_virtual_test_sessions
                       SET status=%s, finished_at=NOW(3), total_samples=%s, note=%s
                     WHERE session_id=%s
                    """,
                    (
                        payload.get("status", "completed"),
                        int(payload.get("total_samples", 0) or 0),
                        payload.get("note", ""),
                        payload.get("session_id", ""),
                    ),
                )
        except Exception as exc:
            print(f">> [DB 에러] 로봇 점검 세션 종료 저장 실패: {exc}")

    def insert_virtual_test_event(self, payload: dict):
        self._ensure_virtual_test_tables()
        cols = self._columns("robot_virtual_test_events")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "payload" in cols and "cycle_index" not in cols:
                    cursor.execute(
                        """
                        INSERT INTO robot_virtual_test_events
                          (session_id, event_type, payload, created_at)
                        VALUES (%s, %s, %s, NOW(3))
                        """,
                        (
                            payload.get("session_id", ""),
                            payload.get("event", payload.get("event_type", "event")),
                            self._json(payload),
                        ),
                    )
                    return

                cursor.execute(
                    """
                    INSERT INTO robot_virtual_test_events
                      (session_id, robot_id, event_type, cycle_index, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        payload.get("session_id", ""),
                        payload.get("robot_id", ""),
                        payload.get("event", payload.get("event_type", "event")),
                        int(payload.get("cycle_index", 0) or 0),
                        self._json(payload),
                    ),
                )
        except Exception as exc:
            print(f">> [DB 에러] 로봇 점검 이벤트 저장 실패: {exc}")

    def insert_virtual_test_sample(self, payload: dict):
        self._ensure_virtual_test_tables()
        cols = self._columns("robot_virtual_test_samples")
        conn = self._get_persistent_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                if "data" in cols:
                    sample_id = payload.get("sample_id")
                    if not sample_id:
                        sample_id = str(payload.get("sample_index", int(time.time() * 1000)))
                    cursor.execute(
                        """
                        INSERT INTO robot_virtual_test_samples
                          (session_id, sample_id, captured_at, data)
                        VALUES (%s, %s, NOW(3), %s)
                        """,
                        (payload.get("session_id", ""), str(sample_id), self._json(payload)),
                    )
                    return

                q = self._six(payload.get("q"))
                p = self._six(payload.get("p"))
                tq = self._six(payload.get("torque"))
                cursor.execute(
                    """
                    INSERT INTO robot_virtual_test_samples
                      (session_id, robot_id, cycle_index, sample_index, busy,
                       q1, q2, q3, q4, q5, q6,
                       x, y, z, rx, ry, rz,
                       tq1, tq2, tq3, tq4, tq5, tq6)
                    VALUES
                      (%s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload.get("session_id", ""),
                        payload.get("robot_id", ""),
                        int(payload.get("cycle_index", 0) or 0),
                        int(payload.get("sample_index", 0) or 0),
                        int(payload.get("busy", 0) or 0),
                        *q,
                        *p,
                        *tq,
                    ),
                )
        except Exception as exc:
            print(f">> [DB 에러] 로봇 점검 샘플 저장 실패: {exc}")


db_repository = DatabaseRepository()
