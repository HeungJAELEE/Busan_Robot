import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager

try:
    import pymcprotocol
except ImportError:
    print(">> pymcprotocol 모듈이 필요합니다. (pip install pymcprotocol)")
    pymcprotocol = None

print("⚙️ [PLC Bridge] 시작됨 - MSA 환경")

def main():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    plc_ip = os.getenv("PLC_IP", "192.168.3.39")
    plc_port = 5000
    
    mqtt_client = MqttManager(broker_ip=broker_ip, client_id="plc_bridge")
    mqtt_client.connect_and_loop()

    if pymcprotocol is None:
        print(" -> PLC 통신 라이브러리가 없어 더미 모드로 동작합니다.")
        while True:
            time.sleep(1)

    pymc3e = pymcprotocol.Type3E()
    pymc3e.setaccessopt(commtype="binary")
    
    print(f" -> PLC({plc_ip}:{plc_port}) 접속 시도 중...")
    try:
        pymc3e.connect(plc_ip, plc_port)
        print(" -> PLC 연결 성공!")
    except Exception as e:
        print(f" -> PLC 연결 실패: {e}. 주기적 재시작을 권장합니다.")
        return

    # 예: D1000(제품 도착 센서) 이전 상태 기억
    prev_sensor = 0

    while True:
        try:
            # D1000 레지스터 1워드 읽기
            wordunits_values = pymc3e.batchread_wordunits(headdevice="D1000", readsize=1)
            current_sensor = wordunits_values[0]

            # 상태가 0에서 1로 변했을 때 (센서 감지)
            if current_sensor == 1 and prev_sensor == 0:
                print(">> [PLC] 부품 도착 감지! MQTT 브로드캐스트")
                mqtt_client.publish("plc/sensor/part_arrived", {"status": 1})
            
            prev_sensor = current_sensor

        except Exception as e:
            print(f" -> PLC 폴링 에러: {e}")
            break

        time.sleep(0.1) # 100ms 주기로 폴링

if __name__ == "__main__":
    main()
