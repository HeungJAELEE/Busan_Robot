import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager

try:
    import cv2
except ImportError:
    print(">> OpenCV 모듈이 필요합니다. (pip install opencv-python-headless)")
    cv2 = None

print("👁 [Vision YOLO] 시작됨 - MSA 환경")

def main():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    mqtt_client = MqttManager(broker_ip=broker_ip, client_id="vision_yolo")
    mqtt_client.connect_and_loop()

    if cv2 is None:
        print(" -> OpenCV가 설치되어 있지 않아 더미 모드로 동작합니다.")
        while True:
            time.sleep(1)

    print(" -> 카메라(/dev/video0) 영상 스트림 캡처 시작...")
    # 예시: 카메라 0번
    # cap = cv2.VideoCapture(0)
    
    while True:
        # 실제 환경 주석 해제:
        # ret, frame = cap.read()
        # if not ret: continue
        
        # 모델 추론 (YOLOv8 등)
        # results = model(frame)
        # 픽셀 좌표 -> mm 변환 로직 ...
        
        # 임시 더미 데이터 발생 (5초마다 물건 하나 발견했다고 가정)
        time.sleep(5)
        detected_pos = {"x": 150.5, "y": 200.0, "class": "box"}
        print(f">> [Vision] 객체 탐지 완료: {detected_pos}")
        
        # 로봇이 바로 잡으러 갈 수 있도록 MQTT 발행
        mqtt_client.publish("vision/target_coord", detected_pos)

if __name__ == "__main__":
    main()
