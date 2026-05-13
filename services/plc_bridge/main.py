import time
import os

print("⚙️ [PLC Bridge] 시작됨")
print(f" -> 대상 PLC IP: {os.getenv('PLC_IP', '192.168.3.39')}")

def main():
    while True:
        # TODO: pymcprotocol 로 미쓰비시 PLC 주기적 폴링
        # D1000 레지스터 값이 변경되면 MQTT 토픽 발행 (센서 감지)
        time.sleep(1)

if __name__ == "__main__":
    main()
