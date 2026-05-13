import time

print("🌍 [Digital Twin] 시작됨")
print(" -> 3D 웹소켓 스트리밍 서버 오픈 (Port: 8080)")

def main():
    while True:
        # TODO: MQTT 브로커에서 로봇 실시간 좌표(robot/status) 구독
        # 웹 브라우저 클라이언트들에게 웹소켓으로 좌표 브로드캐스트
        time.sleep(1)

if __name__ == "__main__":
    main()
