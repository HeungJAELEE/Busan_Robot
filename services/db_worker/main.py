import time

print("🗄 [DB Worker] 시작됨")
print(" -> MQTT 브로커 구독 대기 중...")

def main():
    while True:
        # TODO: MQTT 토픽(robot/status, robot/task_done) 구독
        # 수신 시 database_repository.py 를 통해 MES DB에 Insert/Upsert
        time.sleep(1)

if __name__ == "__main__":
    main()
