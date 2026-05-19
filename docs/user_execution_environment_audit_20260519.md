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
frontend/core/runtime_config.py의 코드 기본값도 HMI_MQTT_AUTOCONNECT=false 기준으로 정리했다.
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

## 7. 작업자가 당황할 수 있는 지점 전체 체크리스트

### A. Git / 업데이트

증상:

```text
git pull을 했는데 화면이나 설정이 안 바뀐다.
```

확인:

```powershell
git status
git branch
git pull origin main
```

주의:

```text
backend\.env는 Git으로 덮어쓰지 않는 로컬 설정 파일이다.
따라서 git pull을 해도 예전 IP, 예전 HMI_MQTT_AUTOCONNECT, 예전 DB 정보가 남을 수 있다.
새 PC 또는 설정 꼬임이 의심되면 backend\.env와 backend\.env.example을 비교한다.
```

### B. 실행 위치

증상:

```text
no configuration file provided: not found
```

원인:

```text
backend 폴더가 아닌 곳에서 docker compose를 실행했다.
```

작업자 기준 정답:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose ps
```

### C. Docker Desktop

증상:

```text
failed to connect to the docker API
docker.sock no such file or directory
```

원인:

```text
Docker Desktop이 꺼져 있거나 Engine이 아직 준비되지 않았다.
```

작업자 기준 정답:

```text
Docker Desktop 실행 -> 왼쪽 아래 Engine running 확인 -> 다시 명령 실행
```

### D. UI와 Docker 역할 혼동

작업자 기준 정리:

```text
UI 화면은 Docker Desktop 안에서 뜨지 않는다.
UI는 Python으로 실행한다.
Docker는 MQTT, Robot Controller, DB Worker, Digital Twin 같은 백그라운드 서비스만 실행한다.
```

권장 실행:

```powershell
deployment\windows\start_robot_controller.bat
```

UI만 켤 때:

```powershell
deployment\windows\start_hmi_ui.bat
```

### E. GUI 없이 터미널 로그만 반복

증상:

```text
공장 자동화 연속 루프
가상 PLC
가상 로봇
MES 데이터 전송
```

원인:

```text
잘못된 실행 진입점 또는 오래된 로컬 파일을 실행했다.
```

작업자 기준 정답:

```text
Ctrl+C로 종료 후 start_hmi_ui.bat 또는 frontend\run_ui_only.py 실행
```

### F. 연결 버튼과 실제 연결

작업자가 오해하기 쉬운 점:

```text
Docker 컨테이너가 Running이어도 로봇이 연결된 것은 아니다.
UI에서 로봇 통신 연결 버튼을 눌러야 실제 연결을 시도한다.
연결 성공은 robot_controller 응답까지 확인한 뒤 표시된다.
```

확인:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose logs --tail=100 robot_controller
```

### G. Robot A/B/C 선택

작업자 기준 주의:

```text
Page2와 Page3는 상단 Robot A/B/C 선택값을 기준으로 명령과 시뮬레이션을 실행한다.
마지막에 연결한 로봇 기준으로 동작한다고 생각하면 안 된다.
실제 명령 전에는 반드시 화면 상단 선택 로봇과 파일명을 다시 확인한다.
```

### H. JSON 파일 이식

작업자 기준 주의:

```text
JSON의 xyz 좌표는 meter 단위다.
UI 표시는 mm 기준일 수 있다.
예: tcp [0,0,0.21,0,0,0] = Z 210mm
```

확인해야 할 것:

```text
1. TCP 값이 JSON에서 로드됐는지
2. wpList id와 moveList wpList 참조가 깨지지 않았는지
3. program node id/pId 구조가 유지되는지
4. 변수 count, Red, Blue, Green 같은 분기 변수가 초기화되는지
5. Loop count가 의도한 반복 횟수인지
```

### I. Page2 시뮬레이션

작업자 기준 주의:

```text
Page2 Play(가상)는 실제 로봇/DI/DO를 건드리지 않고 JSON 실행 순서를 확인한다.
안전 존은 권장/주의/위험 가이드 표시이며 JSON 자체를 수정하지 않는다.
```

당황 포인트:

```text
DI 조건이 필요한 JSON은 DI가 OFF이면 일부 동작이 안 보일 수 있다.
이것은 파싱 실패가 아니라 조건 미충족일 수 있다.
```

### J. Page3 Dry Run Recording

작업자 기준 주의:

```text
Page3는 실제 DO/툴 출력을 임시로 이벤트화하고, 로봇별 반복 실행/데이터 기록을 확인하는 화면이다.
가상 DI는 작업자가 직접 선택해서 넣을 수 있다.
무조건 ALL ON이 실제 공정 조건과 같지는 않다.
```

데이터 확인:

```text
로컬 저장: 선택한 저장 폴더의 JSONL 파일 확인
MySQL 저장: DB 연결 확인 버튼 후 robot_virtual_test_sessions / robot_virtual_test_samples / robot_virtual_test_events 확인
```

### K. MySQL

작업자가 오해하기 쉬운 점:

```text
UI가 켜진 것과 DB 저장 성공은 별개다.
DB 연결 확인이 실패하면 로컬 JSONL 저장부터 확인한다.
```

기본값:

```text
host: 192.168.3.141
port: 3306
user: guest
password: guest1234
db: faictory_mes
```

### L. 실제 생산 전 최소 확인 순서

작업자 기준 추천 순서:

```text
1. Docker Desktop Engine running 확인
2. start_robot_controller.bat 실행
3. UI 창이 뜨는지 확인
4. Page2에서 Robot A/B/C 선택과 JSON 파일명 확인
5. Play(가상)로 순서/분기/위험 존 확인
6. Page3 Dry Run Recording에서 수동 DI 조건과 저장 위치 확인
7. DB 연결 확인
8. 로봇 통신 연결 버튼 클릭
9. Home/Zero 같은 단일 명령으로 연결 확인
10. 낮은 속도에서 짧은 Loop 실행
11. 완료 카운트와 실제 동작 횟수 일치 확인
12. 문제가 없을 때 실제 공정 속도/반복 횟수로 확대
```

## 8. 현재 코드 기준 결론

```text
작업자가 가장 헷갈릴 수 있었던 자동 연결, 잘못된 실행 진입점, Docker 실행 위치, Robot Controller 응답 전 연결 성공 표시 문제는 현재 코드와 문서에 반영했다.
남은 주의점은 실제 현장 운영 절차 문제에 가깝다.
특히 backend\.env 로컬 설정, Robot A 물리 충돌/토크 상태, DB 권한, DI 조건 프리셋은 현장에서 체크해야 한다.
```
