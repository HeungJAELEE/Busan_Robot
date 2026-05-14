import sys
import os

# 현재 폴더 경로를 파이썬 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from infrastructure.repositories.database_repository import db_repository

print('=============================================')
print('1. 실시간 데이터(각도, 토크) 전송 테스트 시작...')
dummy_status = {
    'q': [10.5, 20.0, 30.5, -15.0, 45.0, 90.0],
    'torque': [1.1, 2.2, 3.3, 0.5, 0.8, 0.2]
}
# db_repository 의 내부 메소드를 직접 호출하여 에러를 화면에 출력하도록 함
try:
    conn = db_repository._get_persistent_connection()
    if conn:
        print("  -> DB 접속 성공!")
        db_repository.insert_realtime_data('Robot_Test', dummy_status)
        print("  -> 실시간 데이터 전송 완료! (robot_realtime_status 테이블 확인)")
    else:
        print("  -> DB 접속 실패 (설정이나 권한 확인)")
except Exception as e:
    print(f"  -> 예외 발생: {e}")

print('\n2. 작업 완료 이력(Pick/Place) 전송 테스트 시작...')
dummy_pos = [0.35, -0.45, 0.2, 180.0, 0.0, 180.0]
try:
    db_repository.insert_task_completion('Robot_Test', 'Pick', dummy_pos)
    print("  -> 작업 이력 전송 완료! (robot_task_history 테이블 확인)")
except Exception as e:
    print(f"  -> 예외 발생: {e}")
print('=============================================')
