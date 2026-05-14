import sys
import os
import time

# 프로젝트 루트 경로를 시스템 패스에 추가하여 공통 모듈 임포트 허용
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.infrastructure.mqtt_manager import MqttManager
from src.infrastructure.database_repository import db_repository

print("🗄 [DB Worker] 시작됨 - MSA 환경")

def on_realtime_data(payload):
    """로봇 실시간 상태 수신 콜백"""
    robot_id = payload.get("robot_id", "Unknown")
    db_repository.insert_realtime_data(robot_id, payload)

def on_task_done(payload):
    """작업 완료 이벤트 수신 콜백"""
    robot_id = payload.get("robot_id", "Unknown")
    action_type = payload.get("action_type", "Unknown")
    pos = payload.get("pos", [0,0,0,0,0,0])
    db_repository.insert_task_completion(robot_id, action_type, pos)

def main():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    print(f" -> MQTT 브로커({broker_ip}) 연결 및 구독 대기 중...")
    
    mqtt_client = MqttManager(broker_ip=broker_ip, client_id="db_worker")
    mqtt_client.subscribe("robot/realtime", on_realtime_data)
    mqtt_client.subscribe("robot/task_done", on_task_done)
    
    mqtt_client.connect_and_loop()

    # 메인 스레드 유지
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
