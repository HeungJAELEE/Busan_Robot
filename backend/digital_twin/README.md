# 🌍 Digital Twin 서비스

이 마이크로서비스는 Page 1 Auto / Monitor 화면을 내부망 브라우저에서 볼 수 있게 하는 **읽기 전용 웹 모니터 + 데이터 스트리밍 서버**입니다.

```text
로봇 컨트롤러 PC: http://localhost:8080
내부망 다른 PC:  http://<Robot Controller PC IPv4>:8080
상태 JSON:       http://<Robot Controller PC IPv4>:8080/health
WebSocket:       ws://<Robot Controller PC IPv4>:8080/ws
```

웹 모니터는 로봇 명령을 내리지 않습니다. 실제 제어는 기존 HMI 프로그램에서만 수행합니다.

---

## 🧩 아키텍처 및 통신 구조

```mermaid
flowchart LR
    MQTT((📮 MQTT Broker))
    Browser[(🌐 Browser<br/>Page 1 Web Monitor)]
    
    subgraph Digital Twin Service
        S[MQTT Subscriber]
        HTTP[HTTP Server<br/>Port 8080]
        WS[WebSocket /ws]
    end

    MQTT -->|1. subscribe<br/>'robot/realtime'| S
    S -->|2. 좌표 데이터 패키징| WS
    HTTP -->|index.html| Browser
    WS -->|3. JSON 실시간 스트리밍| Browser
```

## 🛠 주요 기능 (Features)

1. **Page 1 웹 모니터**
   - `http://host:8080` 주소로 접속하면 레일/Robot A/B/C/차량 공정 화면을 표시합니다.
   - 로봇 상태가 없어도 기본 자세를 표시하고, `robot/realtime`이 들어오면 실시간으로 갱신합니다.

2. **실시간 3D 뷰어용 웹소켓 서버**
   - 로봇 컨트롤러나 프론트엔드에서 수집하여 MQTT로 뿌려지는 `robot/realtime` (초당 10회 이상) 데이터를 읽어들입니다.
   - 읽어들인 6축 조인트 각도(`[j1, j2, j3, j4, j5, j6]`) 데이터를 웹소켓(`ws://0.0.0.0:8080/ws`)을 통해 브라우저 클라이언트에게 밀어줍니다(Push).
   
3. **완전한 비종속성 (Decoupling)**
   - 이 서버는 로봇과 직접 소켓(IndyDCP)을 연결하지 않습니다. 오직 MQTT 데이터만 중계하므로, 트래픽이 몰려 웹소켓 서버가 터지더라도 로봇 제어 코어에는 1밀리초의 지연도 주지 않습니다.

## 🏗 내부 구조 (스켈레톤 트리)

```text
digital_twin/
├── requirements.txt            # aiohttp 및 MQTT 패키지
├── Dockerfile                  # 컨테이너 빌드 파일
├── tests/                      # TDD 테스트 코드
│   └── test_digital_twin.py
└── src/                        # 🧠 메인 소스 코드
    ├── main.py                 # HTTP/WebSocket 진입점 (Asyncio 루프)
    ├── web/
    │   └── index.html          # Page 1 내부망 웹 모니터
    ├── core/
    │   └── twin_engine.py      # 실시간 좌표 동기화/필터링 로직
    └── infrastructure/
        ├── mqtt_manager.py     # MQTT 브로커 구독
        └── websocket_server.py # legacy placeholder
```

## 🚀 실행 및 테스트

```bash
# 개별 모듈 단위 테스트 (TDD)
cd backend/digital_twin
python -m pytest tests/

# 수동 단독 실행 (로컬 테스트용)
python src/main.py
```

Docker 실행:

```bash
cd ../
docker compose up -d message_broker digital_twin
open http://localhost:8080
```
