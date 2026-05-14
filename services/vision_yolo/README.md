# 👁 Vision YOLO 마이크로서비스

이 모듈은 실시간 카메라 영상(RTSP 스트림 또는 USB 웹캠)을 가져와 YOLO 등 딥러닝 추론을 수행하고, 화면 내의 부품 위치(X, Y)를 탐지해 MQTT로 뿌려주는 비전 전담 모듈입니다.
무거운 GPU 연산이 이곳에서만 단독으로 실행되어 메인 로봇 컨트롤러의 부하를 줄여줍니다.

## 🏗 폴더 구조 (OOD & TDD)
- `src/main.py`: 서비스 진입점 (OpenCV 프레임 캡처 루프)
- `src/domain/`: 픽셀 좌표 -> 물리 좌표(mm) 변환 로직 등
- `src/infrastructure/`: 카메라 디바이스 I/O, 모델 로딩 및 MQTT 매니저
- `tests/`: `pytest`를 이용한 단위 테스트

## 🚀 개발 및 실행 방법
1. **VSCode DevContainer 환경**
   - 이 폴더를 VSCode로 열고 `Reopen in Container`를 실행하면 모든 파이썬 환경이 자동으로 세팅됩니다.
2. **테스트 실행 (TDD)**
   - 터미널에서 `pytest tests/` 입력
3. **단독 실행**
   - `python src/main.py`
