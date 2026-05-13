import time

print("👁 [Vision YOLO] 시작됨")
print(" -> 카메라 디바이스 접근 및 추론 루프 대기 중...")

def main():
    while True:
        # TODO: OpenCV VideoCapture 로 프레임 획득 -> YOLO 추론
        # 픽셀 좌표를 mm 좌표로 변환 후 MQTT 토픽(vision/detected) 발행
        time.sleep(1)

if __name__ == "__main__":
    main()
