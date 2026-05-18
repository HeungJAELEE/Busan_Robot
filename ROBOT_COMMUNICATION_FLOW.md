# Robot Communication Flow

이 문서는 Indy7 HMI에서 로봇, UI, DB, Digital Twin이 데이터를 주고받는 기준을 정리합니다.

## 1. 핵심 원칙

최종 운영 구조에서는 **Robot Controller가 로봇 소켓 통신을 독점**합니다.

```text
UI
→ MQTT robot/command
→ Robot Controller
→ IndyDCP / Robot
→ MQTT robot/realtime
→ DB Worker / Digital Twin / UI
```

DB Worker와 Digital Twin은 로봇에 직접 접속하지 않습니다. 둘 다 `robot/realtime` JSON을 받아서 자기 역할만 수행합니다.

## 2. 역할 분리

| 모듈 | 역할 |
|---|---|
| Frontend UI | 사용자가 누른 버튼/티칭 실행을 `robot/command` JSON으로 발행 |
| Robot Controller | 로봇 소켓 연결 독점, 명령 실행, 상태 읽기, realtime 발행 |
| MQTT Broker | Topic 기반 메시지 중계 |
| DB Worker | `robot/realtime`, `robot/task_done`, `robot/virtual_test_*`를 MySQL에 저장 |
| Digital Twin | `robot/realtime`을 WebSocket 클라이언트에 전달 |
| Vision YOLO | 감지 좌표를 `vision/target_coord`로 발행 |
| PLC Bridge | 센서 이벤트를 `plc/sensor/part_arrived`로 발행 |

## 3. 쓰기 통신

UI는 로봇에 직접 명령하지 않고 아래 topic으로 명령을 발행할 수 있습니다.

Topic:

```text
robot/command
```

Payload:

```json
{
  "command_id": "uuid",
  "robot_id": "Robot A",
  "type": "task_move_to",
  "args": {
    "p": [100.0, -200.0, 120.0, 0.0, 180.0, 0.0]
  },
  "source": "frontend_gateway_proxy",
  "created_at": 1778932573.0
}
```

지원 command type:

```text
connect
disconnect
joint_move_to
task_move_to
joint_move_by
task_move_by
go_home
go_zero
stop_motion
stop_emergency
stop_current_program
reset_robot
set_do
set_default_tcp
reset_default_tcp
set_reference_frame
reset_reference_frame
set_joint_vel_level
set_task_vel_level
set_collision_level
set_servo
set_brake
direct_teaching
```

Robot Controller는 결과를 아래 topic으로 응답합니다.

```text
robot/result
robot/error
robot/connection
```

## 4. 읽기 통신

Robot Controller는 연결된 로봇 상태를 주기적으로 읽어서 아래 topic으로 발행합니다.

Topic:

```text
robot/realtime
```

Payload:

```json
{
  "robot_id": "Robot A",
  "ip": "192.168.3.7",
  "q": [0.0, 0.0, -90.0, 0.0, -90.0, 0.0],
  "p": [100.0, -200.0, 120.0, 0.0, 180.0, 0.0],
  "torque": [0.1, 0.2, 0.1, 0.0, 0.3, 0.1],
  "di": [0, 0, 1, 0],
  "do": [1, 0, 0, 0],
  "busy": 0,
  "status": {
    "busy": 0,
    "movedone": 1,
    "error": 0,
    "collision": 0,
    "emergency": 0
  },
  "source": "robot_controller",
  "created_at": 1778932573.0
}
```

## 5. DB 저장 흐름

DB Worker는 로봇을 읽지 않습니다. MQTT JSON을 받아서 DB에 저장합니다.

```text
robot/realtime
→ robot_realtime_status

robot/task_done
→ robot_task_history

robot/virtual_test_sample
→ robot_virtual_test_samples

robot/virtual_test_event
→ robot_virtual_test_events
```

## 6. Digital Twin 흐름

Digital Twin도 로봇을 읽지 않습니다.

```text
robot/realtime
→ digital_twin
→ WebSocket ws://0.0.0.0:8080
→ 브라우저/3D 뷰어
```

## 7. UI 실행 모드

UI는 두 가지 방식으로 동작할 수 있습니다.

```text
ROBOT_CONTROL_MODE=direct
```

UI가 직접 IndyDCP로 로봇에 연결합니다. Offline 테스트나 단독 티칭에 적합합니다.

```text
ROBOT_CONTROL_MODE=mqtt
```

UI가 로봇 직접 연결을 하지 않고 Docker Robot Controller로 명령을 위임합니다. Online 운영에 적합합니다.

기본값은 `auto`입니다. MQTT Broker가 연결되어 있으면 gateway를 사용하고, 아니면 기존 direct 방식을 사용합니다.

## 8. 권장 운영 구조

```text
Windows PC
├─ Frontend UI
│  └─ Python으로 실행
│
└─ Docker Backend
   ├─ message_broker
   ├─ robot_controller
   ├─ db_worker
   ├─ digital_twin
   └─ plc_bridge
```

운영 모드에서는 로봇 소켓을 여러 곳에서 동시에 잡지 않도록 `robot_controller`가 로봇 통신 주체가 되어야 합니다.
