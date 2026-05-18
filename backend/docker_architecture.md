# Docker Microservices Architecture 🐳

현재 통합되어 있는 `Indy7_HMI_Clean` 시스템을 6개의 모듈로 분리하여 Docker 컨테이너 기반의 분산 아키텍처로 전환하기 위한 설계 가이드입니다.

## 🎯 왜 6개로 나누나요?
- **장애 격리 (Fault Isolation)**: 카메라(YOLO)가 과부하로 다운되더라도, 로봇 컨트롤러나 PLC 통신은 멈추지 않고 굴러가야 합니다.
- **확장성 (Scalability)**: 카메라나 DB 처리가 밀리면 해당 컨테이너만 자원을 늘릴 수 있습니다.
- **언어 및 환경 독립**: 비전은 Python 3.10(PyTorch), 웹 UI는 Node.js, 로봇 코어는 C++이나 Python 3.11 등 각 모듈에 가장 적합한 환경을 독립적으로 쓸 수 있습니다.

---

## 🏗 모듈 상세 역할 및 통신 흐름

### 1. 🤖 로봇 컨트롤러 (Robot Controller)
- **역할**: 로봇 제어의 심장. IndyDCP 소켓 통신을 통해 로봇에게 좌표 이동, Joint 제어 명령을 내립니다.
- **설계**: HMI(UI)에서 직접 로봇과 소켓을 맺지 않습니다. 컨트롤러가 로봇과 독점 연결을 유지하며, 다른 모듈들에게는 MQTT나 REST API 형태로 '대행' 해줍니다.

### 2. 🌍 디지털 트윈 (Digital Twin)
- **역할**: 로봇의 3D 형상을 웹이나 외부 클라이언트에게 렌더링.
- **설계**: `로봇 컨트롤러`가 MQTT로 10Hz씩 쏴주는 `j_pos` 데이터를 구독(Subscribe)하여 화면을 업데이트합니다. 로봇에 직접 접속 부하를 주지 않습니다.

### 3. 👁 카메라 및 YOLO 스레드 (Vision)
- **역할**: RTSP 스트림이나 USB 웹캠 영상을 실시간으로 분석하여 픽셀을 물리 좌표(mm)로 변환.
- **설계**: 무거운 GPU 연산이 필요합니다. 분석된 객체의 (X, Y) 좌표를 MQTT `vision/detected_objects` 토픽으로 던집니다. 로봇 컨트롤러는 이 토픽만 듣고 이동합니다.

### 4. ⚙️ PLC 연동 (PLC Bridge)
- **역할**: PLC master의 공정 시작/정지/로봇 완료/공정 종료 접점을 읽어서 MQTT와 DB에 기록합니다.
- **설계**: 미쓰비시 MC Protocol 라이브러리가 도는 독립 스레드. `X11`, `X12`, `X145`, `M1150`, `M1130`, `M1120`의 상승 엣지를 감지하면 `plc/process/start`, `plc/process/stop`, `plc/robot/complete`, `plc/process/done` 이벤트를 발행합니다.

### 5. 📮 중앙 통신 브로커 (Communication)
- **역할**: 모든 컨테이너들이 서로 소통할 수 있도록 이어주는 MQTT Broker (Mosquitto) 또는 Redis Pub/Sub 서버.
- **장점**: 모듈끼리 서로의 IP를 몰라도, `topic` 이름만 알면 통신이 가능해집니다.

### 6. 🗄 DB 연동 (MES Worker)
- **역할**: HMI나 UI에서 DB 로직을 완전히 분리. 
- **설계**: "실시간 데이터" 토픽과 "작업 완료" 토픽을 상시 구독(Subscribe)하고 있다가, 데이터가 들어오는 즉시 PyMySQL을 통해 `192.168.3.45` 로 UPSERT 및 INSERT를 수행합니다.

---

## 🔄 데이터 통신 시나리오 예시 (Pick & Place)

1. **PLC master**: `Y160`을 Robot `DI0`으로 물리 출력해 로봇 시작 조건을 만듭니다.
2. **Robot**: 펜던트/JSON 로직에 따라 동작하고 완료 신호를 PLC `X145`로 돌려줍니다.
3. **PLC Bridge**: `X11/X12/X145/M1150/M1130/M1120` 신호 변화를 MQTT 이벤트로 발행합니다.
4. **DB 워커**: PLC 이벤트를 듣고 `plc_process_events` 테이블에 Insert합니다.

> 위와 같이 구성하면 **각 모듈은 오직 본인의 역할에만 집중**할 수 있어 시스템이 극도로 견고해집니다!
