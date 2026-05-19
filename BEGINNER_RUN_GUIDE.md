# Indy7 HMI 초보자 실행 가이드

이 문서는 처음 실행하는 사람 기준으로 작성한 안내서입니다.

현장 배포는 담당 PC별로 나눠서 보는 것이 가장 쉽습니다.

- Robot Controller PC 담당자: [ROBOT_CONTROLLER_PC_SETUP.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/ROBOT_CONTROLLER_PC_SETUP.md)
- Vision / YOLO PC 담당자: [VISION_YOLO_PC_SETUP.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/VISION_YOLO_PC_SETUP.md)
- 전체 배포 전략: [DEPLOYMENT_STRATEGY.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/DEPLOYMENT_STRATEGY.md)

가장 먼저 이것만 기억하면 됩니다.

- **UI 화면**은 Docker Desktop 안에서 뜨지 않습니다.
- **UI 화면**은 Python으로 직접 실행합니다.
- **Docker**는 MQTT, DB Worker, Digital Twin, Robot Controller 같은 백그라운드 서비스를 실행합니다.
- Docker Desktop에서 봐야 하는 곳은 `Images`가 아니라 보통 **Containers** 화면입니다.
- UI는 기본적으로 **무연결 모드**로 켜집니다. 로봇/PLC/MySQL은 사용자가 `연결` 버튼을 눌렀을 때만 붙습니다.
- Page 1/2의 3D 화면에는 초록/주황/빨강 위험 가이드와 rail/place 투명 존이 표시됩니다. 이 표시는 실제 JSON을 바꾸지 않는 확인용 안내입니다.
- Robot A의 2026-05-18 테스트 분석과 다음날 테스트 순서는 [docs/robot_a_dry_run_analysis_20260518.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/docs/robot_a_dry_run_analysis_20260518.md)를 보세요.
- Windows 작업자 기준 실행환경 점검 결과는 [docs/user_execution_environment_audit_20260519.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/docs/user_execution_environment_audit_20260519.md)를 보세요.

## 1. 전체 실행 순서

```text
1. Windows PC에 Docker Desktop 설치
2. 프로젝트 폴더 준비
3. backend/.env 파일 확인
4. Docker 백그라운드 서비스 실행
5. frontend UI 실행
6. 통신 정상 여부 확인
```

## 2. UI 실행 방법

UI는 Docker가 아니라 Python으로 실행합니다.

### Windows에서 실행

PowerShell을 엽니다.

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean
py -m pip install -r requirements.txt
py frontend\run_ui_only.py
```

`requirements.txt`는 기본 HMI, Page 3 로컬/MySQL 저장, Docker 백엔드 연동 클라이언트에 필요한 묶음입니다. Vision YOLO와 화면 캡처 보조 도구는 기본 설치에 넣지 않았습니다.

만약 `py` 명령이 안 되면 아래처럼 시도합니다.

```powershell
python -m pip install -r requirements.txt
python frontend\run_ui_only.py
```

정상이라면 `INDY7 COMMAND CENTER` 창이 뜹니다.

Windows 현장 PC에서는 더 쉽게 아래 파일을 더블클릭해도 됩니다.

```text
deployment\windows\start_hmi_ui.bat
```

주의: `frontend` 폴더 안에서 `python main.py`를 직접 실행하지 마세요. 예전 로컬 파일이 남아 있으면 GUI 대신 공장 자동화 루프 로그만 계속 올라올 수 있습니다. GUI는 `frontend\run_ui_only.py` 또는 `deployment\windows\start_hmi_ui.bat`로 실행합니다.

화면 캡처 테스트 스크립트가 필요할 때만 추가로 실행합니다.

```powershell
py -m pip install -r requirements-dev.txt
```

### Mac에서 실행

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean
python3 -m pip install -r requirements.txt
cd frontend
python3 run_ui_only.py
```

## 3. Docker 설치 방법 (Windows)

### 3-1. WSL2 설치

관리자 권한 PowerShell을 열고 실행합니다.

```powershell
wsl --install
```

설치 후 Windows를 재부팅합니다.

> 참고: `wsl`은 Windows 전용 명령입니다. Mac에서 실행하면 `command not found`가 뜨는 것이 정상입니다.

### 3-2. Docker Desktop 설치

Docker Desktop for Windows를 설치합니다.

- 설치 중 `Use WSL 2 instead of Hyper-V` 옵션을 선택합니다.
- 설치 후 Docker Desktop을 실행합니다.
- 화면 왼쪽 아래 또는 상태 표시가 `Engine running`이면 정상입니다.

설치 확인:

```powershell
docker version
docker compose version
```

정상이라면 Docker Client/Server 버전과 Docker Compose 버전이 표시됩니다.

## 4. Docker 실행 방법

Docker 명령은 반드시 `backend` 폴더에서 실행합니다.

### 4-1. backend 폴더로 이동

Windows:

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean\backend
```

Mac:

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/backend
```

현재 폴더에 `docker-compose.yml`이 있는지 확인합니다.

Windows:

```powershell
dir docker-compose.yml
```

Mac:

```bash
ls docker-compose.yml
```

`docker-compose.yml`이 안 보이면 `docker compose` 명령은 실패합니다.

### 4-2. .env 파일 만들기

Windows:

```powershell
copy .env.example .env
notepad .env
```

Mac:

```bash
cp .env.example .env
open -e .env
```

현장 IP를 확인합니다.

```env
ROBOT_A_IP=192.168.3.7
ROBOT_B_IP=192.168.3.6
ROBOT_C_IP=192.168.3.5
ROBOT_A_PLC_IP=192.168.3.150
ROBOT_B_PLC_IP=192.168.3.140
ROBOT_C_PLC_IP=192.168.3.120
ROBOT_AUTOCONNECT=0
ROBOT_CONTROL_MODE=auto
HMI_MQTT_AUTOCONNECT=0
HMI_MQTT_CONNECT_WAIT_SEC=3
ROBOT_GATEWAY_CONNECT_TIMEOUT_SEC=8
FACTORY_ORCHESTRATOR_AUTOSTART=0
MYSQL_HOST=192.168.3.141
PLC_IP=192.168.3.150
PLC_PORT=2000
PLC_MONITOR_IP=192.168.3.160
PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
```

여기서 제일 중요한 값은 `ROBOT_AUTOCONNECT=0`, `HMI_MQTT_AUTOCONNECT=0`, `FACTORY_ORCHESTRATOR_AUTOSTART=0`입니다. 이 값이면 프로그램을 켜도 실제 장비나 MQTT에 바로 붙지 않고, 화면에서 연결 버튼을 눌렀을 때만 접속합니다.

### 4-3. Docker 서비스 실행

처음 실행하거나 소스에서 직접 빌드할 때:

```powershell
docker compose build
docker compose up -d message_broker db_worker digital_twin
```

실제 로봇까지 연결할 때:

```powershell
docker compose up -d robot_controller
```

PLC까지 연결할 때:

```powershell
docker compose up -d plc_bridge
```

이 PLC 브리지는 쓰기 명령을 보내는 장치가 아니라, 현장 PLC master의 `X11/X12/X145/M1150/M1130/M1120` 상태를 읽어서 MQTT와 DB에 기록하는 감시 장치입니다.

운영 모드에서 UI가 로봇을 직접 잡지 않고 Docker Robot Controller를 통해 제어하게 하려면 UI 실행 전에 아래 환경변수를 켭니다.

Windows:

```powershell
$env:ROBOT_CONTROL_MODE="mqtt"
```

Mac:

```bash
export ROBOT_CONTROL_MODE=mqtt
```

기본값은 `auto`입니다. MQTT Broker가 연결되어 있으면 Docker Robot Controller를 사용하고, 없으면 기존 직접 연결 방식을 사용합니다.

전체 종료:

```powershell
docker compose down
```

## 5. Docker Desktop에서 확인하는 방법

Docker Desktop을 열고 왼쪽 메뉴에서 **Containers**를 클릭합니다.

정상이라면 `indy7-hmi` 프로젝트 아래에 아래 컨테이너들이 보입니다.

```text
indy7_mqtt_broker
indy7_db_worker
indy7_digital_twin
indy7_robot_controller
indy7_plc_bridge
```

초록색 또는 `Running`이면 실행 중입니다.

`Images` 메뉴는 빌드된 이미지 목록을 보는 곳입니다. 프로그램 화면이 나오는 곳이 아닙니다.

## 6. 통신 정상 실행 여부 확인

### 6-1. 컨테이너 상태 확인

`backend` 폴더에서 실행합니다.

```powershell
docker compose ps
```

정상 예시:

```text
indy7_mqtt_broker      Up
indy7_db_worker        Up
indy7_digital_twin     Up
indy7_robot_controller Up
```

### 6-2. MQTT 브로커 확인

```powershell
docker compose logs -f message_broker
```

정상 로그:

```text
mosquitto version ... running
Opening ipv4 listen socket on port 1883
Opening ipv4 listen socket on port 9001
```

### 6-3. Digital Twin 확인

```powershell
docker compose logs -f digital_twin
```

정상 로그:

```text
Digital Twin 시작됨
3D 뷰어용 웹소켓 스트리밍 서버 오픈 (ws://0.0.0.0:8080)
```

### 6-4. Robot Controller 확인

```powershell
docker compose logs -f robot_controller
```

정상 연결 예시:

```text
IndyDCP(192.168.3.7, NRMK-Indy7) 로봇 접속 시도...
실시간 상태 10Hz 폴링 및 MQTT 브로드캐스트 시작
```

아래 로그가 나오면 Docker 문제가 아니라 PC가 로봇 네트워크에 연결되지 않은 상태입니다.

```text
Socket connection error: timed out
로봇 연결 실패. 더미 모드로 폴링합니다.
```

### 6-5. DB Worker 확인

```powershell
docker compose logs -f db_worker
```

아래 로그가 나오면 Docker 문제라기보다 MySQL 서버에 접근하지 못하는 상태입니다.

```text
Can't connect to MySQL server on '192.168.3.141'
```

현장 PC가 MySQL 서버와 같은 네트워크에 있어야 합니다.

### 6-6. PLC Bridge 확인

```powershell
docker compose logs -f plc_bridge
```

아래 로그가 나오면 PLC IP/포트 또는 네트워크 연결을 확인합니다.

```text
PLC 연결 실패: timed out
```

## 6-7. 3D 위험 존 확인

UI를 실행한 뒤 Page 1 또는 Page 2의 `Play(가상)` 화면을 봅니다.

```text
녹색: 권장 안전
주황: 감속/확인 권장
빨강: 회피/분리 테스트 권장
투명 박스: rail, Place 하강 감시, 로봇 간 작업영역 겹침 안내
```

현장 기준 치수:

```text
Robot A/B/C 간격: 185cm
로봇과 rail 사이 거리: 50cm
Robot A부터 rail 끝단까지: 약 100cm
```

주의:

```text
3D 위험 존은 안내용입니다.
실제 충돌이 발생하면 즉시 정지하고 에러 리셋 후 Home으로 복귀합니다.
충돌이 난 상태에서 반복 테스트를 계속 밀어넣지 않습니다.
```

## 7. 네트워크 확인 명령

Windows PowerShell에서 실행합니다.

로봇 A:

```powershell
Test-NetConnection 192.168.3.7 -Port 6066
```

PLC:

```powershell
Test-NetConnection 192.168.3.39 -Port 5000
```

MySQL:

```powershell
Test-NetConnection 192.168.3.141 -Port 3306
```

정상이라면 `TcpTestSucceeded : True`가 나옵니다.

`False`가 나오면 Docker 문제가 아니라 네트워크, IP, 방화벽, 장비 전원, 장비 포트를 확인해야 합니다.

## 8. 자주 나는 에러

### no configuration file provided: not found

원인: `docker-compose.yml`이 없는 폴더에서 실행했습니다.

해결:

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean\backend
docker compose ps
```

### zsh: command not found: wsl

원인: Mac에서 Windows 명령을 실행했습니다.

해결: Mac에서는 `wsl`을 쓰지 않습니다.

### zsh: command not found: docker

원인: Docker Desktop이 설치되지 않았거나 실행되지 않았습니다.

해결: Docker Desktop 설치 후 실행하고 다시 확인합니다.

```bash
docker version
```

### Docker Desktop에 UI 화면이 안 보임

정상입니다.

Docker Desktop은 백그라운드 서비스 상태를 보는 도구입니다. 실제 HMI UI는 Python으로 실행합니다.

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean\frontend
py run_ui_only.py
```

## 9. 현장 실행 최소 명령 모음

Windows PowerShell:

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean\backend
copy .env.example .env
notepad .env
docker compose build
docker compose up -d message_broker db_worker digital_twin
docker compose up -d robot_controller plc_bridge
docker compose ps
```

UI 실행:

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean
py -m pip install -r requirements.txt
cd frontend
py run_ui_only.py
```
