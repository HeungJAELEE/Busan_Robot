# 👁 Vision YOLO 서비스

이 마이크로서비스는 공장에 설치된 **산업용 카메라나 웹캠의 영상을 실시간으로 캡처**하고, **AI 딥러닝 모델(YOLOv8)**을 활용해 부품이나 불량품을 인식하는 역할을 합니다.

---

## 🧩 아키텍처 및 통신 구조

```mermaid
flowchart LR
    Cam[📹 Camera<br/>Webcam / GigE]
    MQTT((📮 MQTT Broker))
    
    subgraph Vision YOLO Service
        Op[OpenCV Capture]
        AI[YOLOv8 Inference Engine<br/>PyTorch/TensorRT]
        Calc[Pixel to mm Converter]
        Pub[MQTT Publisher]
    end

    Cam -->|1. 비디오 프레임 (30fps)| Op
    MQTT -.->|2. (선택적) 트리거 신호<br/>'plc/sensor/part_arrived'| AI
    Op -->|3. 이미지 전달| AI
    AI -->|4. Bounding Box 검출| Calc
    Calc -->|5. 카메라 픽셀 좌표를<br/>로봇 실제 좌표(mm)로 변환| Pub
    Pub -->|6. 퍼블리시<br/>'vision/target_coord'| MQTT
```

## 🛠 주요 기능 (Features)

1. **실시간 객체 인식 (Realtime Object Detection)**
   - `Ultralytics YOLOv8` 등 최신 AI 모델을 탑재하여, 프레임이 들어올 때마다 찾고자 하는 타겟(박스, 볼트, 너트 등)의 화면 상 위치(Pixel)를 찾아냅니다.
   - GPU 자원을 가장 많이 소모하기 때문에 이 모듈을 도커로 완전히 격리하는 것이 MSA 아키텍처의 핵심입니다.

2. **픽셀 → 물리 좌표 변환 (Coordinate Transform)**
   - 화면에서 찾은 `(X=150px, Y=200px)` 좌표는 로봇 입장에서 아무 의미가 없습니다.
   - 사전 캘리브레이션(Calibration) 매트릭스를 적용해 이를 로봇 베이스 기준의 `(X=350.5mm, Y=-150.2mm)` 물리 좌표로 변환합니다.

3. **이벤트 트리거 추론 (Triggered Inference)**
   - 하루 종일 GPU를 풀가동하지 않습니다. 평소에는 대기하다가 PLC Bridge로부터 "컨베이어에 물건 도착"(`plc/sensor/part_arrived`) 신호를 MQTT로 받았을 때만 순간적으로 사진을 찍어 연산합니다.

## 🏗 내부 구조 (스켈레톤 트리)

```text
vision_yolo/
├── requirements.txt            # OpenCV, Ultralytics, PyTorch 등
├── Dockerfile                  # 컨테이너 빌드 파일 (GPU 지원 등)
├── tests/                      # TDD 테스트 코드
│   └── test_vision.py
└── src/                        # 🧠 메인 소스 코드
    ├── main.py                 # 진입점 (트리거 대기)
    ├── core/
    │   ├── yolo_inference.py   # AI 모델 추론 및 Bounding Box 계산
    │   └── coordinate_calc.py  # 픽셀 좌표를 로봇 물리 좌표(mm)로 변환
    └── infrastructure/
        ├── mqtt_manager.py     # 좌표 발행 및 PLC 트리거 구독
        └── camera_capture.py   # 웹캠/산업용 카메라 프레임 확보
```

## 🚀 실행 및 테스트

```bash
# 개별 모듈 단위 테스트 (TDD)
cd backend/vision_yolo
python -m pytest tests/

# 수동 단독 실행 (로컬 테스트용)
python src/main.py
```
