# 사용자 실행환경 재검토 보고서 2026-05-19

이 문서는 작업자가 Windows Robot Controller PC에서 프로그램을 실제로 실행한다는 기준으로 점검한 결과이다.

## 1. 실행 진입점

권장 실행:

```text
deployment\windows\start_robot_controller.bat
deployment\windows\start_hmi_ui.bat
python frontend\run_ui_only.py
```

확인 결과:

```text
frontend/main.py 기본값은 UI-only다.
FACTORY_ORCHESTRATOR_AUTOSTART=1을 명시하지 않으면 legacy PLC/MES orchestrator가 자동 실행되지 않는다.
```

사용자 주의:

```text
GUI 없이 터미널에 공장 자동화 루프 로그만 계속 올라오면 잘못된 실행 파일 또는 오래된 로컬 파일을 실행한 것이다.
그 경우 Ctrl+C로 끄고 start_hmi_ui.bat 또는 frontend\run_ui_only.py를 실행한다.
```

## 2. 자동 연결 정책

현장 기본 정책:

```text
ROBOT_AUTOCONNECT=0
HMI_MQTT_AUTOCONNECT=0
FACTORY_ORCHESTRATOR_AUTOSTART=0
```

의미:

```text
UI 창이 뜨는 것만으로 Robot/PLC/MySQL/MQTT에 붙지 않는다.
로봇 연결은 사용자가 로봇 통신 연결 버튼을 눌렀을 때만 실행된다.
PLC/DB/MQTT 확인은 서비스 관리 또는 통신체크 화면에서 사용자가 시작한다.
```

수정 사항:

```text
기본 .env와 Windows setup 스크립트의 HMI_MQTT_AUTOCONNECT를 0으로 정리했다.
사용자가 Docker를 켜지 않은 상태에서도 UI가 조용히 먼저 뜨도록 했다.
```

## 3. MQTT Robot Controller 연결 확인

기존 위험:

```text
MQTT publish가 성공하면 실제 robot_controller 응답 전에도 UI가 연결 성공처럼 보일 수 있었다.
robot_controller가 꺼져 있거나 실제 로봇 연결 실패일 때 작업자가 오해할 가능성이 있었다.
```

수정 사항:

```text
RobotClientManager.connect()가 connect 명령 결과를 기다리도록 변경했다.
ROBOT_GATEWAY_CONNECT_TIMEOUT_SEC 기본값은 8초다.
HMI_MQTT_CONNECT_WAIT_SEC 기본값은 3초다.
응답 timeout, robot_controller 미기동, 실제 로봇 연결 실패이면 UI가 연결 성공으로 표시하지 않는다.
```

## 4. Docker 실행 위치

반드시 실행할 위치:

```text
Indy7_HMI_Clean\backend
```

실패 증상:

```text
no configuration file provided: not found
```

원인:

```text
docker-compose.yml이 없는 폴더에서 docker compose 명령을 실행했다.
```

확인 명령:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
dir docker-compose.yml
docker compose ps
```

## 5. Page2 / Page3 사용자 동작 기준

Page2:

```text
상단 Robot A/B/C 선택값이 3D 시뮬레이션 안전 존 표시에도 직접 전달된다.
마지막 연결 로봇 기준으로 안전 존이 표시되는 혼동을 줄였다.
```

Page3:

```text
Dry Run Recording은 runner의 현재 program_path를 사용한다.
virtual_di_mode=manual일 때 UI에서 누른 DI가 조건 판정에 사용된다.
실시간 샘플은 q, p, torque, busy, cycle_index를 로컬 JSONL과 MySQL에 저장할 수 있다.
```

class3_test.7.json 재검증:

```text
DI 없음: DI10 대기에서 정지
DI10/11/12/13 ON: Red/Blue/Green 각각 1번 위치 -> 2번 위치 순서
DI10/13 ON, DI11/12 OFF: Green만 정상 실행
```

## 6. 남은 운영상 주의점

```text
1. Docker 컨테이너 Running은 백엔드 준비 상태일 뿐, 실제 로봇 연결 성공을 뜻하지 않는다.
2. 로봇 연결 성공은 UI 연결 버튼 후 robot_controller 응답과 robot/connection 이벤트로 확인한다.
3. Robot A 토크/충돌 에러는 프로그램 문법보다 실제 자세, TCP, 속도, Place 하강 존을 별도로 테스트해야 한다.
4. MySQL이 꺼져 있어도 UI는 켜질 수 있다. DB 기록이 필요한 경우 Page3에서 DB 연결 확인을 먼저 누른다.
5. PLC Bridge는 감시/기록용으로 쓰고, 메인 공정 통제권은 PLC가 가진다는 전제를 유지한다.
```
