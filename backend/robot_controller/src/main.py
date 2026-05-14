import sys
import os
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager
from src.infrastructure.indy_utils import indydcp_client

print("🤖 [Robot Controller] 시작됨 - MSA 환경")

def on_robot_command(payload):
    """외부에서 오는 로봇 제어 명령 수신 (Move, Jog 등)"""
    cmd_type = payload.get("type")
    print(f">> [명령 수신] {cmd_type} 실행...")
    # TODO: 실제 indy 인스턴스에명령 하달 (예: inst.task_move_to(...))

def main():
    robot_ip = os.getenv("ROBOT_IP", "192.168.3.11")
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    robot_name = "Indy7"
    
    mqtt_client = MqttManager(broker_ip=broker_ip, client_id="robot_controller")
    mqtt_client.subscribe("robot/command", on_robot_command)
    mqtt_client.connect_and_loop()

    # Indy 로봇 연결
    print(f" -> IndyDCP({robot_ip}) 로봇 접속 시도...")
    inst = indydcp_client.IndyDCPClient(robot_ip, "Indy7")
    connected = inst.connect()
    
    if not connected:
        print(" -> 로봇 연결 실패. 더미 모드로 폴링합니다.")
        inst = None

    print(" -> 실시간 상태 10Hz 폴링 및 MQTT 브로드캐스트 시작")
    
    while True:
        try:
            if inst:
                j_pos = inst.get_joint_pos()
                torque = inst.get_control_torque()
                busy = inst.get_robot_status().get('busy', 0)
            else:
                j_pos, torque, busy = [0]*6, [0]*6, 0

            status_data = {
                "robot_id": robot_name,
                "q": j_pos,
                "torque": torque,
                "busy": busy
            }
            # HMI나 DB Worker가 받을 수 있도록 10Hz로 계속 뿌림
            mqtt_client.publish("robot/realtime", status_data)
            
        except Exception as e:
            # print(f"폴링 에러: {e}")
            pass
            
        time.sleep(0.1)

if __name__ == "__main__":
    main()
