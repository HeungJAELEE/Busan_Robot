# 🖥️ Frontend — Indy7 HMI Desktop Application

이 폴더는 Indy7 로봇을 조종하는 **데스크톱 GUI(화면) 프로그램**입니다.
Docker가 아닌, PC의 터미널에서 직접 실행합니다.

처음 실행하는 사용자는 루트의 [`BEGINNER_RUN_GUIDE.md`](../BEGINNER_RUN_GUIDE.md)를 먼저 확인하세요.

## 🚀 실행 방법
```bash
# 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 로봇 제어 + UI 실행
python run_ui_only.py
```

## 🏗 내부 구조 (스켈레톤 트리)

나중에 코드를 수정할 때 한눈에 파악할 수 있도록 작성된 파일 구조도입니다.

```text
frontend/
├── run_ui_only.py                       # [진입점] 로봇 제어 UI 전용 실행 파일
├── main.py                              # [진입점] 통합 시스템 실행 파일 (더 방대한 세팅 시)
├── requirements.txt                     # 프론트엔드 전용 파이썬 패키지 목록
│
├── core/                                # 🧠 비즈니스 로직 (두뇌)
│   ├── service_manager.py               # 백그라운드 데몬 스레드 관리자 (MQTT, DB 등 ON/OFF 제어)
│   └── domains/robot/
│       ├── communication/client_manager.py # 로봇 소켓 인스턴스 싱글톤 관리
│       └── use_cases/robot_control_usecase.py # JSON 모션을 실제 로봇 명령으로 변환 (Pick/Place 연산)
│
├── infrastructure/                      # 🔌 외부 연동
│   ├── mqtt/mqtt_manager.py             # MQTT Pub/Sub 클라이언트
│   └── repositories/database_repository.py # DB 직접 연결이 필요할 때 사용하는 레포지토리
│
├── presentation/ui/                     # 🖥️ 사용자 화면 (GUI)
│   ├── main_window.py                   # 메인 프레임 (네비게이션, 서비스 토글, 터미널 로그)
│   ├── theme.py                         # Deep Space Command Center 컬러/글꼴 테마
│   │
│   ├── digital_twin/                    # [Page 1] 
│   │   └── digital_twin_view.py         # 3D 뷰어 화면 (그래프 및 모니터링)
│   │
│   └── robot_hmi/                       # [Page 2]
│       ├── robot_hmi_view.py            # 티칭 화면 전체 프레임 (JSON 파싱 및 트리 실행)
│       └── editors/                     # 우측 패널 (노드별 상세 설정 편집기)
│
├── indy_utils/                          # 🤖 로봇 통신 SDK
│   └── indydcp_client.py                # 뉴로메카 공식 소켓 통신 라이브러리
│
└── user_programs/                       # 📄 사용자 데이터
    └── Indy7/program.json               # APK에서 추출한 로봇 작업 프로그램 (뼈대)
```

## 🧩 주요 시스템 흐름 및 동작 원리

### 0. 🌐 Frontend 통신 아키텍처 다이어그램
프론트엔드는 단순한 화면(View)을 넘어, 로봇 및 여러 백그라운드 서비스들과 실시간으로 소통하는 **통합 지휘 통제소** 역할을 합니다.

```mermaid
flowchart TD
    %% 프론트엔드 내부 블록
    subgraph Frontend [🖥️ Frontend Desktop UI (main_window.py)]
        UI[사용자 조작 화면<br/>Tkinter GUI]
        SM[ServiceManager<br/>Thread Controller]
        Parser[JSON 파싱 엔진<br/>robot_hmi_view]
        Poller[텔레메트리 폴링<br/>10Hz]
    end

    %% 통신 채널
    MQTT((📮 MQTT Broker<br/>pub/sub))
    IndyDCP((🤖 IndyDCP<br/>Socket))

    %% 백그라운드 서비스
    subgraph Backend Services [백그라운드 서비스 스레드]
        DB[🗄 DB Worker]
        DT[🌍 Digital Twin]
        PLC[⚙️ PLC Bridge]
        Vis[👁 Vision YOLO]
    end

    %% 연결 관계
    UI -->|1. 서비스 ON/OFF 제어| SM
    SM -.->|Thread 실행| DB
    SM -.->|Thread 실행| DT
    SM -.->|Thread 실행| PLC
    SM -.->|Thread 실행| Vis

    UI -->|2. 로봇 제어 명령/티칭| Parser
    Parser -->|3. TCP/IP 제어| IndyDCP
    
    Poller -->|4. 초당 10번 좌표/토크 요청| IndyDCP
    IndyDCP -.->|응답| Poller
    
    Poller -->|5. 좌표 데이터 브로드캐스트| MQTT
    MQTT -->|구독| DB & DT
    
    Parser -->|6. Pick/Place 작업 완료 통보| MQTT
    MQTT -->|구독| DB
```

### 1. 🧵 스레드(Thread) 기반 서비스 제어 (`core/service_manager.py`)
프론트엔드 UI 창 하나에서 다양한 백그라운드 서비스(비전, DB, 통신 등)를 제어합니다.
- UI 메인 창은 tkinter의 `mainloop()`가 점유하므로 멈추면 안 됩니다.
- 따라서 우측 상단의 **[🔌 서비스 관리]** 토글을 누르면, `ServiceManager`가 각 기능을 파이썬의 **데몬 스레드(Daemon Thread)**로 개별 실행합니다.
- 각 스레드는 `stop_event`를 주입받아, 사용자가 OFF 버튼을 누르면 안전하게 루프를 빠져나와 종료됩니다.

### 2. 📡 실시간 텔레메트리 (`main_window._poll_loop`)
- UI가 켜지면 0.1초마다 로봇에 `get_task_pos()`, `get_joint_pos()`, `get_control_torque()`를 호출합니다.
- 수집된 데이터는 화면 3D 뷰어에 표시됨과 동시에, `MQTT(robot/realtime)` 토픽으로 무한정 퍼블리시됩니다.
- (Digital Twin이나 DB Worker 스레드는 이 토픽을 구독하여 각자 할 일을 합니다.)

### 3. 🧠 로봇 프로그램 파싱 엔진 (`robot_hmi_view._execute_node_list`)
- APK에서 USB로 빼온 JSON 파일을 읽습니다.
- 트리 뷰를 위에서부터 아래로 순회하며 동작을 수행합니다.
- Pick(201)이나 Place(202) 노드를 만나면 `robot_control_usecase.py`를 호출하여 **Approach -> Target(Hold/Release) -> Retract** 3단계 시퀀스 모션을 자동으로 생성해 로봇 모터를 움직입니다.

### 4. 🛑 긴급 정지 (`robot_control_usecase.wait_for_move_finish`)
- 프로그램 동작 중 '정지' 버튼을 누르면 `_global_stop` 플래그가 켜집니다.
- 루프 내에서 로봇 이동을 기다리는 동안 0.05초마다 이 플래그를 검사하여, 즉시 로봇 동작을 중단(`stop_motion()`)하고 스레드를 빠져나옵니다.
