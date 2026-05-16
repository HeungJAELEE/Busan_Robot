import json
import os
import pymysql
import threading
import time
from contextlib import contextmanager

class DatabaseRepository:
    """
    외부 MySQL 데이터베이스(faictory_mes)와 통신하여
    로봇의 실시간 데이터와 작업 이력 데이터를 전송하는 레포지토리.
    """
    _instance = None
    _lock = threading.Lock()
    
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', os.getenv('MYSQL_HOST', '192.168.3.45')),
        'port': int(os.getenv('DB_PORT', os.getenv('MYSQL_PORT', '3306'))),
        'user': os.getenv('DB_USER', os.getenv('MYSQL_USER', 'guest')),
        'password': os.getenv('DB_PASS', os.getenv('MYSQL_PASSWORD', 'guest1234')),
        'db': os.getenv('DB_NAME', os.getenv('MYSQL_DATABASE', 'faictory_mes')),
        'charset': 'utf8mb4',
        'autocommit': True,
        'use_unicode': True,
        'connect_timeout': 5,
        'init_command': "SET NAMES utf8mb4"
    }

    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._virtual_tables_ready = False

    def _get_persistent_connection(self):
        """단일 persistent 커넥션을 유지하며, 끊기면 자동 재연결합니다."""
        with self._lock:
            if self._conn is None:
                try:
                    self._conn = pymysql.connect(**self.DB_CONFIG)
                except Exception as e:
                    print(f">> [DB 에러] 연결 실패: {e}")
                    return None
            else:
                try:
                    self._conn.ping(reconnect=True)
                except Exception as e:
                    print(f">> [DB 에러] ping 실패 재연결 중: {e}")
                    try:
                        self._conn = pymysql.connect(**self.DB_CONFIG)
                    except:
                        return None
            return self._conn

    def _ensure_virtual_test_tables(self):
        if self._virtual_tables_ready:
            return
        conn = self._get_persistent_connection()
        if not conn:
            return
        queries = [
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_sessions (
                session_id VARCHAR(96) PRIMARY KEY,
                robot_id VARCHAR(64) NOT NULL,
                program_path TEXT,
                target_cycles INT DEFAULT 0,
                sample_interval_ms INT DEFAULT 100,
                dry_run TINYINT DEFAULT 1,
                status VARCHAR(32) DEFAULT 'running',
                started_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                finished_at DATETIME(3) NULL,
                total_samples INT DEFAULT 0,
                note TEXT
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_samples (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(96) NOT NULL,
                robot_id VARCHAR(64) NOT NULL,
                cycle_index INT DEFAULT 0,
                sample_index BIGINT DEFAULT 0,
                busy TINYINT DEFAULT 0,
                q1 DOUBLE, q2 DOUBLE, q3 DOUBLE, q4 DOUBLE, q5 DOUBLE, q6 DOUBLE,
                x DOUBLE, y DOUBLE, z DOUBLE, rx DOUBLE, ry DOUBLE, rz DOUBLE,
                tq1 DOUBLE, tq2 DOUBLE, tq3 DOUBLE, tq4 DOUBLE, tq5 DOUBLE, tq6 DOUBLE,
                captured_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                INDEX idx_virtual_session_cycle (session_id, cycle_index),
                INDEX idx_virtual_robot_time (robot_id, captured_at)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(96) NOT NULL,
                robot_id VARCHAR(64) NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                cycle_index INT DEFAULT 0,
                payload LONGTEXT,
                created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                INDEX idx_virtual_event_session (session_id, event_type)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
        ]
        try:
            with conn.cursor() as cursor:
                for query in queries:
                    cursor.execute(query)
            self._virtual_tables_ready = True
        except Exception as e:
            print(f">> [DB 에러] 가상화 테스트 테이블 준비 실패: {e}")

    def insert_realtime_data(self, robot_id: str, status_data: dict):
        """
        로봇의 실시간 데이터(각 축 각도, 토크 등)를 DB에 저장합니다.
        ON DUPLICATE KEY UPDATE를 사용하여 한 로봇당 하나의 최신 레코드만 유지합니다.
        """
        query = """
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
        """
        
        q = status_data.get('q', [0]*6)
        tq = status_data.get('torque', [0]*6)
        
        values = (
            robot_id,
            q[0], q[1], q[2], q[3], q[4], q[5],
            tq[0], tq[1], tq[2], tq[3], tq[4], tq[5]
        )

        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                conn.commit()
        except Exception as e:
            pass

    def insert_task_completion(self, robot_id: str, action_type: str, pos: list):
        """
        Pick/Place 동작 완료 시, 해당 동작의 목적지 XYZ 좌표를 DB에 남깁니다.
        - action_type: 'Pick' 또는 'Place'
        - pos: [x, y, z, u, v, w] (task_pos)
        """
        # TODO: 실제 구축하신 테이블 구조에 맞게 컬럼명 수정 필요!
        query = """
            INSERT INTO robot_task_history 
            (robot_id, action_type, pos_x, pos_y, pos_z, completed_at) 
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        
        # x, y, z 좌표 추출
        px, py, pz = pos[0], pos[1], pos[2]
        values = (robot_id, action_type, px, py, pz)

        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                conn.commit()
                    # print(f">> [DB] {action_type} 동작 기록 완료: X={px:.3f}, Y={py:.3f}, Z={pz:.3f}")
        except Exception as e:
            print(f">> [DB 에러] {action_type} 이력 저장 실패: {e}")

    @staticmethod
    def _six(values):
        result = list(values or [])[:6]
        while len(result) < 6:
            result.append(0.0)
        return [float(v or 0.0) for v in result]

    def upsert_virtual_test_session(self, payload: dict):
        self._ensure_virtual_test_tables()
        query = """
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
        """
        values = (
            payload.get("session_id", ""),
            payload.get("robot_id", ""),
            payload.get("program_path", ""),
            int(payload.get("target_cycles", 0) or 0),
            int(payload.get("sample_interval_ms", 100) or 100),
            1 if payload.get("dry_run", True) else 0,
            payload.get("status", "running"),
            payload.get("note", ""),
        )
        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
        except Exception as e:
            print(f">> [DB 에러] 가상화 세션 저장 실패: {e}")

    def finish_virtual_test_session(self, payload: dict):
        self._ensure_virtual_test_tables()
        query = """
            UPDATE robot_virtual_test_sessions
               SET status=%s, finished_at=NOW(3), total_samples=%s, note=%s
             WHERE session_id=%s
        """
        values = (
            payload.get("status", "completed"),
            int(payload.get("total_samples", 0) or 0),
            payload.get("note", ""),
            payload.get("session_id", ""),
        )
        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
        except Exception as e:
            print(f">> [DB 에러] 가상화 세션 종료 저장 실패: {e}")

    def insert_virtual_test_event(self, payload: dict):
        self._ensure_virtual_test_tables()
        query = """
            INSERT INTO robot_virtual_test_events
              (session_id, robot_id, event_type, cycle_index, payload)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            payload.get("session_id", ""),
            payload.get("robot_id", ""),
            payload.get("event", payload.get("event_type", "event")),
            int(payload.get("cycle_index", 0) or 0),
            json.dumps(payload, ensure_ascii=False),
        )
        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
        except Exception as e:
            print(f">> [DB 에러] 가상화 이벤트 저장 실패: {e}")

    def insert_virtual_test_sample(self, payload: dict):
        self._ensure_virtual_test_tables()
        q = self._six(payload.get("q"))
        p = self._six(payload.get("p"))
        tq = self._six(payload.get("torque"))
        query = """
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
        """
        values = (
            payload.get("session_id", ""),
            payload.get("robot_id", ""),
            int(payload.get("cycle_index", 0) or 0),
            int(payload.get("sample_index", 0) or 0),
            int(payload.get("busy", 0) or 0),
            *q,
            *p,
            *tq,
        )
        try:
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
        except Exception as e:
            print(f">> [DB 에러] 가상화 샘플 저장 실패: {e}")

# 싱글톤 인스턴스 전역 내보내기
db_repository = DatabaseRepository()
