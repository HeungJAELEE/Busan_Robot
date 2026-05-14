# Indy7 PC-HMI — Deep Space Command Center 🚀

Neuromeka(뉴로메카) **Indy7 협동 로봇**을 위한 PC 기반 HMI 소프트웨어 시스템입니다.

기존의 얽혀있던 구조에서 벗어나 **프론트엔드 UI와 백엔드 마이크로서비스(스레드 기반/도커 기반 선택 가능)를 분리**하여 개발된 클린 아키텍처 기반의 모노레포(Monorepo) 프로젝트입니다.

---

## 📁 프로젝트 모노레포 구조 (Frontend & Backend)

이 프로젝트는 완전히 역할이 분리된 두 개의 핵심 폴더로 구성되어 있습니다.

### 🖥️ 1. Frontend (`frontend/` 폴더)
- **역할**: 로봇 작업자가 화면을 보고 조작하는 **"데스크톱 GUI"** 및 **"비즈니스 로직(두뇌)"**을 담당합니다.
- **핵심 컴포넌트**:
  - `presentation/ui/`: CustomTkinter 기반의 다크 모드, 모던 UI 화면 코드 (Digital Twin 뷰어, 조종 패널 등).
  - `core/domains/`: 로봇 명령 파싱, 모션 계산, JOG 이동 등 핵심 두뇌 역할을 하는 곳입니다.
  - `user_programs/`: APK에서 가져온 JSON 파일들이 이곳에 저장되고 파싱됩니다.
  - `run_ui_only.py`: 시스템을 구동하는 메인 실행 파일입니다.

### 📦 2. Backend (`backend/` 폴더)
- **역할**: 화면에 보이지 않고 백그라운드에서 묵묵히 통신, 연산, DB 저장을 처리하는 **"마이크로서비스 엔진"**입니다.
- **핵심 컴포넌트**:
  - `docker-compose.yml`: 도커 도입 시 이 파일 하나로 전체 백엔드를 띄울 수 있습니다.
  - `db_worker/`: 프론트엔드가 보낸 MQTT 작업 완료 메시지를 받아서 MySQL에 기록합니다.
  - `plc_bridge/`: 현장 장비(미쓰비시 PLC)의 센서 신호를 0.1초마다 폴링합니다.
  - `vision_yolo/`: 웹캠으로 부품을 인식하여 좌표를 변환해 로봇에게 보냅니다.
  - `robot_controller/` / `digital_twin/`: 각각 로봇의 상태를 소켓으로 읽어오거나 3D 웹 브라우저용 웹소켓 서버를 엽니다.

---

## 🚀 어떻게 실행하나요? (빠른 시작)

현재 시스템은 **도커(Docker) 없이도 파이썬 UI 창 하나에서 모든 마이크로서비스를 제어**할 수 있도록 고도화되었습니다.

### 실행 명령어
터미널을 열고 아래 명령어를 입력합니다.
```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/frontend
python run_ui_only.py
```

### 서비스 켜기 (UI 내부 제어)
1. 화면이 뜨면 우측 상단의 **[🔌 서비스 관리]** 버튼을 클릭합니다.
2. 아래로 서비스 제어 패널이 펼쳐집니다.
3. 원하는 서비스의 버튼을 클릭하면, 파이썬 백그라운드 스레드로 **각 서비스가 켜지고 🟢 아이콘**이 표시됩니다.
   - 📮 MQTT Broker: 내부 통신 우체국 (Mosquitto 서버와 연동)
   - ⚙️ PLC Bridge: 미쓰비시 PLC 센서 폴링 연동
   - 👁 Vision YOLO: 웹캠/산업용 카메라 연동 YOLOv8 추론
   - 🗄 DB Worker: 로봇 작업 이력을 MySQL FA DB에 적재
   - 🌍 Digital Twin: 3D 브라우저 뷰어를 위한 웹소켓 서버

---

## 🧠 스레드(Thread) 기반 서비스 구조

이 프로그램은 UI를 멈추지 않게 하면서 무거운 백그라운드 작업들을 동시에 처리하기 위해 **Python 데몬 스레드(Daemon Thread)**를 적극 활용합니다. 

```mermaid
flowchart TD
    subgraph 메인 UI [메인 스레드 (tkinter GUI)]
        A(화면 렌더링 & 버튼 이벤트)
        B(로봇 통신 폴링)
        C(🔌 서비스 관리 패널)
    end

    subgraph Service Manager [백그라운드 스레드 매니저]
        C -->|ON/OFF 토글| SM{ServiceManager.toggle()}
    end

    subgraph 백그라운드 데몬 스레드들
        SM -->|Thread 1| T1[MQTT Broker 상태 모니터링]
        SM -->|Thread 2| T2[PLC 미쓰비시 센서 폴링 루프]
        SM -->|Thread 3| T3[Vision YOLO 카메라 실시간 캡처]
        SM -->|Thread 4| T4[MySQL DB 적재 워커]
        SM -->|Thread 5| T5[Digital Twin 웹소켓 스트리밍 서버]
    end

    B -.->|텔레메트리 퍼블리시| T1
    T2 -.->|센서 감지 퍼블리시| T1
```
* **특징**: `frontend/core/service_manager.py`가 각 서비스를 완전히 독립된 Thread로 할당하여 구동시킵니다.
* 에러가 발생해도(예: DB 접속 실패, 카메라 단선) 해당 스레드만 내부적으로 종료되고 **전체 로봇 조종 UI는 절대 죽지 않도록 예외 처리**되어 있습니다.

---

## ⚖️ 도커(Docker) 도입 시나리오 및 관리 방안

현재는 하나의 파이썬 앱 내에서 스레드를 쪼개는 방식을 쓰고 있어 사용이 매우 편하지만, 공장 환경에 납품하거나 서버 수준의 무중단 서비스가 필요할 때는 **Docker 마이크로서비스 구조**로 전환할 수 있습니다. (현재 프로젝트 `backend/` 폴더 내에 도커 구조가 완벽하게 준비되어 있습니다.)

### 스레드 기반 (현재 방식) vs 도커 기반 (MSA)

| 비교 항목 | 🧵 스레드 기반 (현재) | 🐳 도커 기반 (도입 시) |
|---|---|---|
| **설치 및 실행** | 매우 쉬움 (`python run_ui_only.py` 끝) | 도커 데스크톱 환경 세팅 필요 (`docker compose up`) |
| **시스템 오버헤드** | 가벼움 (OS 프로세스 1개 메모리 공유) | 다소 무거움 (각각 독립된 리눅스 OS 가상화) |
| **안정성 (장애격리)** | 보통 (심각한 메모리 누수 발생 시 UI 강제종료 가능성) | **최상** (완벽 격리, 비전 프로세스가 터져도 로봇 UI는 생존) |
| **자원 병렬 처리(GPU)** | 파이썬 GIL 한계로 완전한 병렬 처리에 제약이 있음 | 완전한 병렬, YOLO가 컨테이너에서 GPU/CPU 100% 점유 가능 |
| **유지보수 / 배포** | PC 환경마다 의존성 충돌 우려 (PC마다 환경이 다름) | USB에 컨테이너를 담아 이식하면 100% 완벽히 동일한 실행 보장 |

### 🛠 도커 도입 시 유지보수 관리 방안
1. **점진적 분리 (Hybrid)**: 처음부터 다 도커로 바꾸기보다는, UI는 호스트(Windows/Mac)에서 그대로 파이썬으로 띄우고 가장 무거운 **비전(YOLO)과 DB Worker만** 도커 컨테이너로 빼서 분리 운영하는 것이 합리적입니다.
2. **모니터링 체계 (Observability)**: 도커로 쪼개면 로그가 컨테이너별로 흩어집니다. 따라서 향후 `Grafana`나 `ELK(Elasticsearch)` 스택을 함께 띄워, 모든 컨테이너의 에러를 하나의 웹 대시보드에서 볼 수 있도록 세팅해야 운영자가 편합니다.
3. **오토 힐링 (Auto Healing)**: 컨테이너가 이유 없이 죽었을 때 관리자가 일일이 켜줄 필요 없이, `docker-compose.yml` 파일 내에 `restart: always` 옵션을 걸어두어 Docker 데몬이 무한정 자동 재시작 하도록 무중단 시스템을 구성합니다.

---

## 📜 핵심 기능: Conty(APK) JSON 프로그래밍 호환성

이 프로그램의 가장 큰 차별점이자 핵심 무기는 기존 안드로이드 기반 **Conty 티치펜던트(APK)에서 저장한 로봇 작업 JSON 파일**을 PC 데스크톱 프로그램에서 100% 똑같이 읽어들이고, 화면에 띄워 수정하고, 실제 로봇으로 실행할 수 있다는 점입니다.

### 1. JSON 파일 내부 구조 해부

사용자가 USB로 빼온 `program.json` 파일은 4가지 핵심 블록으로 나뉩니다.
* **`info`**: 로봇에 장착된 공구(Tool) 무게, 좌표계 오프셋, 기본 설정 데이터
* **`wpList`**: 티칭된 공간 상의 모든 3D 좌표(Waypoint) 목록. 각 좌표에 고유 식별 번호가 부여됨.
* **`program`**: 실제 동작 흐름을 결정하는 뼈대(트리 구조). 999(Root) 아래에 순서대로 작업 노드들이 매달려 있습니다.
* **`moveList`**: 각 이동 동작 간의 로봇 속도, 가속도, 블렌딩(부드러운 곡선 회전) 등의 상세 설정 정보.

### 2. 작동 흐름 (JSON 파싱 및 로봇 실행 엔진)

이 프로그램이 JSON을 읽어서 로봇을 움직이는 과정은 아래와 같습니다.

```mermaid
flowchart TD
    A[APK에서 가져온 JSON 파일] -->|UI에서 열기| B(frontend/user_programs/로봇명/program.json)
    
    subgraph 1. 파싱 및 UI 변환
        B -->|json.load()| C{파서: _load_program_from_json()}
        C -->|노드 타입별 분류<br/>201, 202, 20...| D((화면 좌측 TreeView에<br/>계층형 시각화 트리로 표시))
    end
    
    subgraph 2. 로봇 코어 제어 엔진
        D -->|▶️ 재생 버튼 클릭| E{코어 모터 루프: _execute_node_list()}
        E -->|type==201| F[Pick 동작 자동 시퀀스 계산<br>Approach 좌표 생성 → 타겟 하강 및 Hold → Retract 상승]
        E -->|type==202| G[Place 동작 자동 시퀀스 계산<br>Approach 좌표 생성 → 타겟 하강 및 Release → Retract 상승]
        E -->|type==20| H[Loop 제어<br>count 수량만큼 하위 자식 노드를 재귀 실행]
    end
    
    F -->|Pick 완료| I[MQTT Broker: publish('robot/task_done')]
    G -->|Place 완료| I
    
    subgraph 3. MES DB 연동 (백그라운드 스레드)
        I -->|이벤트 감지| J[db_worker 스레드]
        J -->|비동기 INSERT| K[(MySQL 로봇작업이력 DB에 영구 기록)]
    end
```

### 3. 노드 타입 코드 매핑 테이블
프로그램 내장 `Node` 클래스 엔진이 JSON에 적힌 단순한 숫자를 인식하여, 복잡한 파이썬 로봇 제어 명령어(`indydcp_client`) 조합으로 즉시 번역합니다.

| type 코드 | 노드 이름 | 실제 수행되는 로봇 메커니즘 |
|---|---|---|
| `999` | Start / Base | 프로그램 최상단 진입점. 초기화 변수들을 적용합니다. |
| `201` | **Pick (잡기)** | `목표점 Z축 + 15cm 이동 대기` → `목표점 실제 하강` → `디지털 출력(그리퍼 닫기)` → `다시 15cm 상승` (3단계 모션 자동 수행) |
| `202` | **Place (놓기)** | `목표점 Z축 + 15cm 이동 대기` → `목표점 실제 하강` → `디지털 출력(그리퍼 열기)` → `다시 15cm 상승` (3단계 모션 자동 수행) |
| `20` | Loop (반복) | 트리에 매달린 자식 노드들을 지정된 횟수(count)만큼 처음부터 다시 실행합니다. |
| `24` | If (조건) | PLC나 외부 디지털 센서 입력 핀(DI)의 True/False 값에 따라 실행할 노드를 바꿉니다. |
| `30` | DO (출력) | 릴레이, 램프, 실린더 등을 구동하기 위해 로봇 컨트롤러의 디지털 핀에 신호를 줍니다. |
| `2` | Move L | 툴 끝단이 완벽한 '직선(Line)'을 그리며 웨이포인트 좌표로 이동시킵니다. |

---

### 💡 JSON → Python 코드 변환 예시 (직관적 이해)

단순한 JSON 데이터가 어떻게 실제 파이썬 로봇 제어 명령(IndyDCP)으로 바뀌는지 보여주는 핵심 예시입니다.

#### 📄 1. 원본 JSON 데이터 (APK에서 추출)
사용자가 안드로이드 태블릿 화면에서 'Pick' 버튼을 누르고 좌표를 저장하면 아래처럼 JSON으로 저장됩니다.
```json
{
  "type": 201,               // 201 = Pick 동작
  "wpId": 5,                 // 5번 웨이포인트(좌표)를 타겟으로 지정
  "name": "박스 집기",
  "data": {
    "speed": 50,             // 이동 속도 50%
    "distance": 0.15         // 타겟에서 15cm 위에서 대기(Approach)
  }
}
```

#### ⚙️ 2. 프론트엔드의 파이썬 객체 변환 (`frontend/core/domains/teaching_management`)
위 JSON을 읽어들여 프론트엔드의 **`Node` 객체**로 매핑합니다.
```python
# JSON의 type: 201을 감지하여 PickNode 클래스로 생성
if node_data["type"] == 201:
    node = PickNode(
        wp_id=node_data["wpId"],
        name=node_data["name"],
        speed=node_data["data"]["speed"],
        approach_distance=node_data["data"]["distance"] # 0.15m (15cm)
    )
    self.tree.add_node(node)  # UI 트리에 그리기
```

#### 🚀 3. 실제 실행 엔진 (`RobotControlUseCase`)
▶️ 재생 버튼을 누르면 내부적으로 아래와 같이 **3단계의 자동 파이썬 코드**가 실행되어 로봇 모터를 움직입니다.

```python
# 1단계: Approach (타겟 위치에서 Z축으로 15cm 위로 이동)
# 목표 좌표의 Z값(높이)에 distance를 더해서 안전한 대기 지점으로 이동합니다.
approach_pos = target_pos.copy()
approach_pos[2] += node.approach_distance  # Z축 + 0.15m
indydcp_client.task_move_to(approach_pos)  # 로봇아, 공중에서 대기해라!
wait_for_move_done()

# 2단계: Target (실제 타겟 위치로 하강하여 그리퍼 잡기)
indydcp_client.task_move_to(target_pos)    # 로봇아, 바닥으로 내려가라!
wait_for_move_done()
indydcp_client.set_do(DO_PIN, True)        # 디지털 출력(DO) ON -> 그리퍼 닫힘! (물건 잡음)
time.sleep(0.5)                            # 0.5초 대기

# 3단계: Retract (물건을 잡고 다시 15cm 공중으로 후퇴)
indydcp_client.task_move_to(approach_pos)  # 로봇아, 다시 공중으로 올라와라!
wait_for_move_done()

# 완료 후 MQTT로 DB에 성공 이력 전송
mqtt.publish("robot/task_done", {"type": "Pick", "pos": target_pos})
```

이처럼 UI는 단순한 JSON 파일만 던져주면, 프론트엔드의 로봇 코어가 **로봇 SDK(`indydcp_client`) 전용 함수로 실시간 번역**하여 로봇을 완벽하게 제어하게 됩니다.
