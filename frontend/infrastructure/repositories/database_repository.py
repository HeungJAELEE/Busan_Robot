import pymysql
import threading
import time
from contextlib import contextmanager
from core.runtime_config import mysql_config

class DatabaseRepository:
    """
    외부 MySQL 데이터베이스(faictory_mes)와 통신하여
    로봇의 실시간 데이터와 작업 이력 데이터를 전송하는 레포지토리.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._operational_tables_ready = False

    def _db_config(self):
        return mysql_config()

    def _get_persistent_connection(self):
        """단일 persistent 커넥션을 유지하며, 끊기면 자동 재연결합니다."""
        with self._lock:
            if self._conn is None:
                try:
                    self._conn = pymysql.connect(**self._db_config())
                except Exception as e:
                    print(f">> [DB 에러] 연결 실패: {e}")
                    return None
            else:
                try:
                    self._conn.ping(reconnect=True)
                except Exception as e:
                    print(f">> [DB 에러] ping 실패 재연결 중: {e}")
                    try:
                        self._conn = pymysql.connect(**self._db_config())
                    except Exception as reconnect_error:
                        print(f">> [DB 에러] 재연결 실패: {reconnect_error}")
                        return None
            return self._conn

    def _ensure_operational_tables(self):
        if self._operational_tables_ready:
            return
        conn = self._get_persistent_connection()
        if not conn:
            return
        queries = [
            """
            CREATE TABLE IF NOT EXISTS robot_realtime_status (
                robot_id VARCHAR(64) PRIMARY KEY,
                j1_deg DOUBLE, j2_deg DOUBLE, j3_deg DOUBLE,
                j4_deg DOUBLE, j5_deg DOUBLE, j6_deg DOUBLE,
                t1_nm DOUBLE, t2_nm DOUBLE, t3_nm DOUBLE,
                t4_nm DOUBLE, t5_nm DOUBLE, t6_nm DOUBLE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS robot_task_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                robot_id VARCHAR(64) NOT NULL,
                action_type VARCHAR(64) NOT NULL,
                pos_x DOUBLE, pos_y DOUBLE, pos_z DOUBLE,
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_task_robot_time (robot_id, completed_at)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
        ]
        try:
            with conn.cursor() as cursor:
                for query in queries:
                    cursor.execute(query)
            self._operational_tables_ready = True
        except Exception as e:
            print(f">> [DB 에러] 운영 테이블 준비 실패: {e}")

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
            self._ensure_operational_tables()
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                conn.commit()
        except Exception as e:
            print(f">> [DB 에러] 실시간 상태 저장 실패: {e}")

    def insert_task_completion(self, robot_id: str, action_type: str, pos: list):
        """
        Pick/Place 동작 완료 시, 해당 동작의 목적지 XYZ 좌표를 DB에 남깁니다.
        - action_type: 'Pick' 또는 'Place'
        - pos: [x, y, z, u, v, w] (task_pos)
        """
        query = """
            INSERT INTO robot_task_history 
            (robot_id, action_type, pos_x, pos_y, pos_z, completed_at) 
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        
        # x, y, z 좌표 추출
        px, py, pz = pos[0], pos[1], pos[2]
        values = (robot_id, action_type, px, py, pz)

        try:
            self._ensure_operational_tables()
            conn = self._get_persistent_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                conn.commit()
                    # print(f">> [DB] {action_type} 동작 기록 완료: X={px:.3f}, Y={py:.3f}, Z={pz:.3f}")
        except Exception as e:
            print(f">> [DB 에러] {action_type} 이력 저장 실패: {e}")

# 싱글톤 인스턴스 전역 내보내기
db_repository = DatabaseRepository()
