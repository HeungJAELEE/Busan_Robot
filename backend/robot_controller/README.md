# 🤖 Robot Controller 서비스

이 마이크로서비스는 실물 **Indy7 협동 로봇**과 직접 소켓통신(IndyDCP)을 맺고 명령을 주고받는 가장 핵심적이고 크리티컬한 하위 백엔드 엔진입니다.

> ⚠️ 현재는 이 서비스의 로직이 `frontend/core/domains/robot`로 많이 이관되어 UI 프로그램 내에서 병합(Thread)되어 실행되고 있습니다. 하지만 다수의 로봇을 동시에 제어하거나 무거운 연산을 분리할 때 이 독립 컨테이너를 다시 활성화합니다.

---

## 🧩 아키텍처 및 통신 구조

```mermaid
flowchart TD
    MQTT((📮 MQTT Broker))
    Robot[🤖 Indy7 실물 로봇<br/>192.168.3.11]
    
    subgraph Robot Controller Service
        Sub[MQTT Subscriber<br/>'robot/command']
        Core[Motion Planner<br/>& Safety Checker]
        DCP[IndyDCP Client SDK]
        Pub[MQTT Publisher<br/>'robot/realtime']
    end

    MQTT -->|1. 이동 명령 (JOG, Task 등)| Sub
    Sub -->|2. 명령 파싱| Core
    Core -->|3. 충돌 방지 및 한계 검사| DCP
    DCP -->|4. TCP 소켓 명령 전송| Robot
    
    Robot -->|5. 100ms마다 좌표/토크 응답| DCP
    DCP -->|6. 상태 수집| Pub
    Pub -->|7. 퍼블리시| MQTT
```

## 🛠 주요 기능 (Features)

1. **명령 릴레이 (Command Relay)**
   - UI나 비전 등 다른 모듈이 MQTT로 던진 추상적인 명령(`{"type":"Move", "pos":[X,Y,Z]}`)을 받아서 실제 로봇 제어기(STEP)가 알아듣는 하위 레벨 API(`task_move_to`)로 번역하여 전송합니다.

2. **안전성 확보 (Safety Layer)**
   - UI에서 들어온 명령 좌표가 로봇의 물리적 한계 범위를 벗어나는지 미리 계산하여, 충돌이나 고장 위험이 있으면 로봇으로 명령을 보내지 않고 에러 이벤트를 반환합니다.

3. **고속 텔레메트리 (High-speed Telemetry)**
   - 로봇에게 10Hz 이상의 속도로 6축 각도, 말단 좌표, 각 관절의 부하(토크) 정보를 뽑아내서 전체 시스템(디지털 트윈, DB 등)이 사용할 수 있도록 브로드캐스트합니다.

## 🏗 내부 구조 (스켈레톤 트리)

```text
robot_controller/
├── requirements.txt            # 로봇 통신 및 MQTT 패키지
├── Dockerfile                  # 컨테이너 빌드 파일
├── tests/                      # TDD 테스트 코드
│   └── test_robot_controller.py
└── src/                        # 🧠 메인 소스 코드
    ├── main.py                 # 진입점 (10Hz 텔레메트리 발행 루프)
    ├── core/
    │   └── safety_planner.py   # 명령 유효성 검사 및 충돌 방지
    └── infrastructure/
        ├── mqtt_manager.py     # 명령 수신 및 상태 발행
        └── indy_client.py      # 실물 로봇 TCP/IP 통신 (IndyDCP)
```

## 🚀 실행 및 테스트

```bash
# 개별 모듈 단위 테스트 (TDD)
cd backend/robot_controller
python -m pytest tests/

# 수동 단독 실행 (로컬 테스트용)
python src/main.py
```
