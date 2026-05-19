# 시스템 요구사항 및 패키지 설치 가이드

이 문서는 `Indy7_HMI_Clean` 최종 배포 기준의 Python 패키지 설치 기준입니다.

## 1. 설치 묶음 구분

| 파일 | 언제 설치하나 | 포함 범위 |
|---|---|---|
| `requirements.txt` | Robot Controller PC 기본 설치 | HMI UI, Page 3 Dry Run Recording, MySQL, MQTT, Robot Controller, PLC Bridge, Digital Twin |
| `frontend/requirements.txt` | 프론트엔드만 따로 개발/실행할 때 | CustomTkinter UI, 3D 그래프, AI Teaching, MySQL/MQTT 클라이언트 |
| `backend/vision_yolo/requirements.txt` | Vision/YOLO PC 또는 비전 컨테이너를 쓸 때만 | OpenCV, ultralytics, torch, torchvision |
| `requirements-dev.txt` | 화면 캡처/디버그 보조 스크립트 실행 시만 | `tkcap` |

## 2. Robot Controller PC 기본 설치

프로젝트 루트에서 실행합니다.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows에서 `python`이 안 되면 아래처럼 실행합니다.

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## 3. Vision YOLO 설치

Vision PC 담당자 또는 비전 컨테이너 개발자만 설치합니다.

```bash
python -m pip install -r backend/vision_yolo/requirements.txt
```

YOLO 패키지는 `torch`, `ultralytics` 때문에 무겁습니다. Robot Controller PC에서 단순 HMI/로봇 제어만 할 때는 기본 설치에 포함하지 않습니다.

## 4. 개발 보조 도구 설치

화면 캡처 테스트(`frontend/presentation/ui/screenshot_test.py`)를 실행할 때만 설치합니다.

```bash
python -m pip install -r requirements-dev.txt
```

현재 확인한 `tkcap` 최신 배포 버전은 `0.0.4`입니다. `tkcap>=0.0.11` 같은 버전은 설치 실패합니다.

## 5. 주요 패키지 역할

| 패키지 | 설치 위치 | 역할 |
|---|---|---|
| `customtkinter` | frontend | HMI 데스크톱 UI |
| `numpy` | frontend, robot_controller | 좌표, 관절, 로봇 수학 계산 |
| `scipy` | frontend | 회전 행렬, 보간, motion math |
| `matplotlib` | frontend | Page 1/2 3D 시각화, 오실로스코프 |
| `paho-mqtt` | frontend, backend services | MQTT 통신 |
| `PyMySQL` | frontend, db_worker | MySQL 연결 및 기록 |
| `cryptography` | frontend, db_worker | MySQL 8 인증 지원 |
| `pymcprotocol` | plc_bridge, frontend | Mitsubishi PLC MC Protocol |
| `websockets` | digital_twin, frontend service helper | Digital Twin WebSocket |
| `google-genai` | frontend | Page 4 Google AI Studio / Gemini Teaching |
| `sounddevice` | frontend | Page 4 마이크 음성 입력 |
| `pyserial` | frontend | 시리얼 장비 보조 |
| `PyYAML` | frontend | 설정 파일 파싱 |
| `Pillow` | frontend | 이미지/아이콘 처리 |
| `opencv-python-headless` | vision_yolo | 카메라 프레임 처리 |
| `ultralytics` | vision_yolo | YOLO 추론 |
| `torch`, `torchvision` | vision_yolo | 딥러닝 런타임 |
| `tkcap` | requirements-dev | 선택 화면 캡처 도구 |

## 6. 설치 검증

```bash
python -m py_compile $(rg --files frontend backend/robot_controller/src backend/db_worker/src backend/plc_bridge/src backend/digital_twin/src -g '*.py')
```

Docker 설정 검증:

```bash
cd backend
docker compose config
```

패키지 설치 가능성만 미리 확인:

```bash
python -m pip install --dry-run -r requirements.txt
python -m pip install --dry-run -r requirements-dev.txt
```

## 7. 오류 대응

| 증상 | 원인 | 조치 |
|---|---|---|
| `ModuleNotFoundError` | 패키지 미설치 | 현재 PC 역할에 맞는 requirements 파일 설치 |
| `pymcprotocol 미설치` | PLC Bridge 패키지 누락 | `python -m pip install -r requirements.txt` |
| `websockets 모듈 필요` | Digital Twin 패키지 누락 | `python -m pip install -r requirements.txt` |
| `google genai 없음` | Page 4 AI 패키지 누락 | `python -m pip install -r frontend/requirements.txt` 또는 root requirements 설치 |
| `tkcap 없음` | 선택 캡처 도구 미설치 | `python -m pip install -r requirements-dev.txt` |
| YOLO 설치가 너무 오래 걸림 | torch/ultralytics가 무거움 | Robot Controller PC에는 기본 설치만 사용 |
