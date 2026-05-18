import json
import pymysql
import threading
import time

from core.runtime_config import mysql_config


class DatabaseRepository:
    """
    프론트엔드 로컬 테스트용 DB 레포지토리.
    현장 DB의 payload JSON 스키마와 기존 컬럼 펼침 스키마를 모두 지원합니다.
    """

    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._columns_cache = {}
        self._operational_tables_ready = False

    def _db_config(self):
        config = dict(mysql_config())
        config.setdefault("charset", "utf8mb4")
        config.setdefault("autocommit", True)
        config.setdefault("use_unicode", True)
        config.setdefault("connect_timeout", 5)
        config.setdefault("init_command", "SET NAMES utf8mb4")
        return config

    def _get_persistent_connection(self):
        """단일 persistent 커넥션을 유지하며, 끊기면 자동 재연결합니다."""
        with self._lock:
            if self._conn is None:
                try:
                    self._conn = pymysql.connect(**self._db_config())
                except Exception as exc:
                    print(f">> [DB 에러] 연결 실패: {exc}")
                    return None
            else:
                try:
                    self._conn.ping(reconnect=True)
                except Exception as exc:
                    print(f">> [DB 에러] ping 실패 재연결 중: {exc}")
                    try:
                        self._conn = pymysql.connect(**self._db_config())
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
        """Pick/Place 동작 완료 이력을 DB에 남깁니다."""
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


db_repository = DatabaseRepository()
