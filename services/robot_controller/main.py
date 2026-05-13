import time
import os

print("🤖 [Robot Controller] 시작됨")
print(f" -> 대상 로봇 IP: {os.getenv('ROBOT_IP', '192.168.3.11')}")

def main():
    while True:
        # TODO: IndyDCP 소켓 연결 유지 및 MQTT로 명령 수신 대기
        # 상태를 10Hz로 읽어서 MQTT(topic: robot/status) 로 발행
        time.sleep(1)

if __name__ == "__main__":
    main()
