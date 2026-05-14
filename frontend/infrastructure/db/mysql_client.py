import pymysql
from typing import List
from core.domains.mes_integration.repositories import IMesRepository

class MySqlMesClient(IMesRepository):
    """MySQL 데이터베이스에 연결하여 MES 데이터를 기록하는 인프라 구현체"""
    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.conn = None

    def connect(self) -> None:
        try:
            self.conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=True
            )
            print("✅ [Infra] MySQL MES 서버 연결 성공!")
            self._create_table_if_not_exists()
        except Exception as e:
            print(f"❌ [Infra] MySQL MES 서버 연결 실패: {e}")
            self.conn = None

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            print("🔌 [Infra] MySQL MES 서버 연결 종료")

    def _create_table_if_not_exists(self):
        if not self.conn: return
        query = """
        CREATE TABLE IF NOT EXISTS robot_motion_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            robot_id VARCHAR(50),
            motion_name VARCHAR(100),
            j1 FLOAT, j2 FLOAT, j3 FLOAT, j4 FLOAT, j5 FLOAT, j6 FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query)

    def log_robot_position(self, robot_id: str, motion_name: str, joint_pos: List[float]) -> None:
        if not self.conn:
            print(f"⚠️ [Infra] DB 연결 없음. 로그 기록 스킵 (Data: {joint_pos})")
            return
            
        try:
            with self.conn.cursor() as cursor:
                query = """
                INSERT INTO robot_motion_logs (robot_id, motion_name, j1, j2, j3, j4, j5, j6)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                j1, j2, j3, j4, j5, j6 = joint_pos[:6]
                cursor.execute(query, (robot_id, motion_name, j1, j2, j3, j4, j5, j6))
                print(f"💾 [MES] 로봇 {robot_id}의 '{motion_name}' 위치 로그 저장 완료")
        except Exception as e:
            print(f"❌ [MES] 로그 저장 실패: {e}")
