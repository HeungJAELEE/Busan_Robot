# Indy7 HMI 코드맵 — 기능별 파일 위치 가이드

> 디버깅/수정 시 **이 파일을 먼저 참조**하여 해당 기능의 정확한 위치로 바로 이동할 것.

프로젝트 루트: `/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/`

---

## 1. 진입점 & 메인 윈도우

| 파일 | 클래스/함수 | 역할 |
|---|---|---|
| `run_ui_only.py` | `main()` | UI만 실행 (하드웨어 없이 테스트) |
| `main.py` | — | 전체 앱 실행 (PLC/MQTT 포함) |
| `presentation/ui/main_window.py` | `ModernContyApp` | 메인 윈도우 (Page 1↔2 전환) |
| ↳ | `switch_page()` :111 | 페이지 전환 |
| ↳ | `toggle_connection()` :122 | 로봇 연결/해제 |
| ↳ | `_poll_loop()` :156 | 실시간 좌표/상태 폴링 |
| `presentation/ui/theme.py` | `Theme` | 디자인 토큰 (색상/폰트 중앙관리) |

---

## 2. Page 1: Auto/Monitor Mode (디지털 트윈)

| 파일 | 클래스 | 역할 |
|---|---|---|
| `presentation/ui/digital_twin/digital_twin_view.py` | `DigitalTwinView` | 3D 뷰어/모니터링 |

---

## 3. Page 2: Setting/Teaching Mode (HMI)

### 3-1. 메인 HMI 뷰

| 파일 | 클래스/함수 | 역할 |
|---|---|---|
| `presentation/ui/robot_hmi/robot_hmi_view.py` | `ProgramTreeEditor` | 프로그램 트리 + 에디터 통합 |
| ↳ | `render()` :558 | 전체 레이아웃 (좌측 버튼 / 중앙 트리 / 우측 에디터) |
| ↳ | `_on_node_selected()` :723 | 트리 노드 선택 → 에디터 표시 |
| ↳ | `_run_program()` :956 | 프로그램 순차 실행 |
| ↳ | `play_simulation()` :404 | 2D 시뮬레이션 |
| ↳ | `save_program()` :69 | JSON 파일 저장 |
| ↳ | `load_program()` :378 | JSON 파일 로드 |

### 3-2. 모션 에디터 (`editors/motion_editors.py`)

| 클래스 | 라인 | 역할 |
|---|---|---|
| `JogController` | :9 | JOG 수동 조작 (Joint/Base/Tool) |
| ↳ `render()` | :17 | JOG 패널 UI |
| ↳ `_toggle_direct_teaching()` | :268 | 다이렉트 티칭 토글 |
| ↳ `_toggle_servo()` | :279 | 서보 ON/OFF 토글 |
| ↳ `_reset_robot()` | :288 | 로봇 리셋 |
| `MoveEditor` | :311 | Joint/Task Move 에디터 |
| `MoveByEditor` | :377 | 상대이동(MoveBy) 에디터 |
| `ForceEditor` | :419 | 힘제어 에디터 |
| `MoveHomeEditor` | :465 | Move Home 에디터 |
| `MoveCEditor` | :475 | 원호이동(MoveC) 에디터 |

### 3-3. 프로세스 에디터 (`editors/process_editors.py`)

| 클래스 | 라인 | 역할 |
|---|---|---|
| `PickPlaceEditor` | :6 | 팔레타이징 + Pick/Place 전체 |
| ↳ `_open_pallet_wizard()` | :312 | 마법사 연동 |
| ↳ `_on_wizard_result()` | :332 | 마법사 결과 반영 콜백 |
| ↳ `_draw_pallet_preview()` | :260 | 미니 캔버스 프리뷰 (패턴별) |
| ↳ `_auto_calc_p2p3()` | :401 | P1 기반 P2/P3/P4 자동 계산 |
| ↳ `_execute_pallet_move()` | :456 | Get/Move 버튼 실행 |
| ↳ `_execute_move_step()` | :468 | Approach-Target-Retract 3단계 |
| ↳ `update_ui()` | :642 | 트리 선택 시 에디터 필드 업데이트 |
| ↳ `apply_changes()` | :720 | 에디터 → 트리 데이터 반영 |
| `VisionEditor` | :808 | 비전 에디터 (PC 전용) |
| `SyncEditor` | :831 | 동기화 에디터 (PC 전용) |
| `SetAOEditor` | :853 | Analog Output 설정 에디터 |

### 3-4. 로직 에디터 (`editors/logic_editors.py`)

| 클래스 | 라인 | 역할 |
|---|---|---|
| `LoopEditor` | :6 | 반복문 (횟수/무한) |
| `MathEditor` | :72 | 변수 연산 |
| `CallEditor` | :120 | 서브 프로그램 호출 |
| `IfEditor` | :153 | DI 조건분기 / 변수 조건분기 |
| `WaitEditor` | :227 | 시간 대기 |
| `WaitDIEditor` | :255 | DI 신호 대기 |
| `DOEditor` | :290 | **DO 출력 설정 (프로그램 트리용)** |
| `CommentEditor` | :307 | 주석 |
| `StopEditor` | :318 | 정지 |
| `SwitchEditor` | :329 | 다중 분기 |
| `FolderEditor` | :346 | 폴더 그룹 |

### 3-5. I/O 모니터 (`editors/io_monitor.py`)

| 클래스/함수 | 라인 | 역할 |
|---|---|---|
| `IOMonitorPanel` | :8 | I/O 대시보드 전체 |
| ↳ `_toggle_do(idx)` | :130 | **DO 버튼 토글 (→ set_do)** |
| ↳ `_toggle_endtool_do(idx)` | :143 | **EndTool DO 토글** |
| ↳ `_on_ao_change(idx, val)` | :155 | AO 슬라이더 변경 |
| ↳ `_toggle_monitoring()` | :160 | 모니터링 시작/정지 |
| ↳ `_monitor_loop()` | :169 | 백그라운드 폴링 (DI/DO/AI 읽기) |

### 3-6. 도구 (`tools/`)

| 파일 | 클래스 | 역할 |
|---|---|---|
| `tools/oscilloscope.py` | `OscilloscopeDialog` | 실시간 그래프 (Joint/Task/F-T) |
| `tools/palletizing_wizard.py` | `PalletizingWizardDialog` | 팔레타이징 마법사 (6패턴) |
| `tools/auto_payload.py` | `AutoPayloadDialog` | 페이로드 자동 측정 |

---

## 4. 로봇 제어 계층 (Core)

### 4-1. 통신 매니저

| 파일 | 클래스 | 역할 |
|---|---|---|
| `core/domains/robot/communication/client_manager.py` | `RobotClientManager` | 싱글톤 로봇 연결 관리 |
| ↳ | `connect()` :48 | IndyDCP 연결 |
| ↳ | `disconnect()` :74 | 연결 해제 |
| ↳ | `get_active_instance()` :40 | 현재 활성 로봇 클라이언트 반환 |
| ↳ | `update_robot_state()` :88 | 좌표/상태 메모장 기록 |

### 4-2. 로봇 제어 유스케이스 (`robot_control_usecase.py`)

> **모든 로봇 명령의 중앙 허브** — UI에서 직접 `indydcp_client`를 호출하지 않고 반드시 이 클래스를 경유.

| 함수 | 라인 | 역할 | 인터락 |
|---|---|---|---|
| `check_interlock()` | :21 | 비상정지/에러/충돌/busy 체크 | — |
| `_guard_motion()` | :60 | 모션 명령 전 인터락 게이트 | — |
| **상태 조회** | | | |
| `get_robot_status()` | :76 | 전체 상태 딕셔너리 | 없음 |
| `get_joint_pos()` | :1109 | 현재 관절 좌표 | 없음 |
| `get_task_pos()` | :1119 | 현재 TCP 좌표 | 없음 |
| `get_ft_sensor()` | :698 | F/T 센서 값 | 없음 |
| **모션 명령** | | | |
| `jog_axis()` | :208 | JOG 이동 | ✅ guard |
| `move_to_joint()` | :232 | 관절 절대이동 | ✅ guard |
| `move_to_task()` | :247 | TCP 절대이동 | ✅ guard |
| `move_by_task()` | :760 | TCP 상대이동 | ✅ guard |
| `move_by_joint()` | :778 | 관절 상대이동 | ✅ guard |
| `move_c()` | :736 | 원호이동 | ✅ guard |
| `go_home()` | :272 | 홈 위치 이동 | 없음 |
| `go_zero()` | :281 | 제로 위치 이동 | 없음 |
| **Digital I/O** | | | |
| `set_do(idx, val)` | :373 | **DO 출력 (0/1)** | ✅ guard |
| `get_di()` | :387 | DI 읽기 (32ch) | 없음 |
| `get_do()` | :398 | DO 상태 읽기 | 없음 |
| `set_endtool_do_port()` | :948 | EndTool DO 설정 | 없음 |
| `get_endtool_di()` | :937 | EndTool DI 읽기 | 없음 |
| **Analog I/O** | | | |
| `set_ao(idx, val)` | :426 | AO 설정 | 없음 |
| `get_ai(idx)` | :439 | AI 읽기 | 없음 |
| **로봇 제어** | | | |
| `stop_robot()` | :294 | 정지 | 없음 |
| `emergency_stop()` | :303 | 비상정지 | 없음 |
| `reset_robot()` | :312 | 리셋 | 없음 |
| `set_servo()` | :325 | 서보 ON/OFF | 없음 |
| `set_brake()` | :340 | 브레이크 ON/OFF | 없음 |
| `direct_teaching()` | :355 | 다이렉트 티칭 ON/OFF | 없음 |
| **프로그램 실행** | | | |
| `start_program()` | :596 | 프로그램 시작 | 없음 |
| `run_json_program()` | :628 | JSON 프로그램 직접 실행 | 없음 |
| `execute_pick_place_sequence()` | :545 | Approach→Target→Retract 시퀀스 | 없음 |
| **고급** | | | |
| `stack_search()` | :1133 | F/T 기반 적재물 높이 탐색 | 없음 |
| `spiral_search()` | :1189 | 나선형 Peg-in-Hole | 없음 |
| `set_payload()` | :799 | 페이로드 설정 | 없음 |
| `set_impedance()` | :862 | 임피던스 제어 | 없음 |
| `math_operation()` | :1077 | 변수 연산 | 없음 |

### 4-3. IndyDCP 클라이언트 (저수준)

| 파일 | 역할 |
|---|---|
| `indy_utils/indydcp_client.py` | IndyDCP 프로토콜 TCP 통신 (절대 직접 호출 금지, UseCase 경유) |
| ↳ `set_do(idx, val)` :1189 | `CMD_SET_SMART_DO` 패킷 전송 |
| ↳ `get_di()` :1181 | `CMD_GET_SMART_DIS` 32채널 읽기 |
| ↳ `get_do()` :1200 | `CMD_GET_SMART_DOS` 읽기 |
| ↳ `set_endtool_do()` :1226 | `CMD_SET_ENDTOOL_DO` (endtool_type + val) |

---

## 5. 인프라 계층

| 파일 | 역할 |
|---|---|
| `infrastructure/plc/pymc_client.py` | 미쓰비시 PLC MC Protocol |
| `infrastructure/mqtt/paho_mqtt_client.py` | MQTT 클라이언트 |
| `infrastructure/db/mysql_client.py` | MySQL MES 연동 |
| `infrastructure/mes/mes_client.py` | MES 비즈니스 로직 |
| `infrastructure/robot_control/conty_executor.py` | Conty JSON 실행기 |

---

## 6. 데이터/티칭 관리

| 파일 | 역할 |
|---|---|
| `core/domains/teaching_management/entities.py` | 티칭 트리 노드 엔티티 |
| `core/domains/teaching_management/services/pallet_calculator.py` | 팔레타이징 좌표 계산 |
| `core/application/use_cases/conty_json_parser.py` | Conty APK JSON 파서 |
| `core/application/use_cases/conty_json_manager.py` | Conty JSON 저장/로드 |
| `core/domains/motion_management/entities.py` | 모션 엔티티 (좌표, 웨이포인트) |
| `core/domains/robot/use_cases/motion_math.py` | 모션 수학 (회전행렬, 좌표변환) |

---

## 7. 디자인 시스템 (`theme.py`)

| 토큰 | 값 | 용도 |
|---|---|---|
| `BG_BASE` | `#060311` | 주 배경 |
| `BG_SURFACE` | `#161320` | 패널/카드 배경 |
| `ACCENT_PRIMARY` | `#5800fd` | 활성 버튼 |
| `SUCCESS` | `#4CAF50` | 성공/ON |
| `DANGER` | `#F44336` | 정지/OFF |
| `WARNING` | `#FF9800` | 경고/주의 |
| `INFO` | `#00BCD4` | 정보 |

---

## 8. 흔한 디버깅 경로

| 증상 | 확인할 파일 | 확인 포인트 |
|---|---|---|
| DO/DI 동작 이상 | `io_monitor.py` → `robot_control_usecase.py` :373 | `_guard_motion` 인터락 + `set_do` 반환값 |
| JOG 안 움직임 | `motion_editors.py` :91 → `robot_control_usecase.py` :208 | `_guard_motion` 체크 |
| 팔레타이징 좌표 틀림 | `process_editors.py` :401 → `motion_math.py` | `_auto_calc_p2p3()` |
| 트리 노드 선택 안됨 | `robot_hmi_view.py` :723 | `_on_node_selected()` |
| 프로그램 저장 안됨 | `robot_hmi_view.py` :69 | `save_program()` |
| 로봇 연결 실패 | `client_manager.py` :48 | `connect()` |
| 페이지 전환 안됨 | `main_window.py` :111 | `switch_page()` |
