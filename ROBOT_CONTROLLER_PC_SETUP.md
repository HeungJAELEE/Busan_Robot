# Robot Controller PC 설치 가이드

이 문서는 Robot Controller PC 한 대에서 아래 기능을 실행하는 방법입니다.

- Robot A/B/C 통신
- HMI UI
- MQTT Broker
- PLC Bridge
- DB Worker
- Digital Twin
- MySQL 저장

Vision A/B/C 카메라 PC 담당자는 이 문서가 아니라 [VISION_YOLO_PC_SETUP.md](/Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/VISION_YOLO_PC_SETUP.md)를 보면 됩니다.

## 1. 기준 PC 사양

권장 최소 사양:

```text
CPU: Intel Core i5-8500 이상
RAM: 16GB 이상
OS: Windows 10/11 64bit
Network: 192.168.3.x 대역 유선 LAN 권장
```

Vision YOLO를 이 PC에서 같이 돌리지 않는 조건이면 위 사양으로 충분합니다.

## 2. 현장 IP 기준

```text
Robot A: 192.168.3.7
Robot B: 192.168.3.6
Robot C: 192.168.3.5

PLC A/main: 192.168.3.150:2000
PLC B/main: 192.168.3.140:2000
PLC C/main: 192.168.3.120:2000
PLC monitor: 192.168.3.160:2000

MySQL: 192.168.3.141:3306
Database: faictory_mes
User: guest
Password: guest1234
```

## 3. Windows 기본 프로그램 설치

관리자 PowerShell을 열고 그대로 붙여넣습니다.

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.11 -e
winget install --id Docker.DockerDesktop -e
```

설치 후 Windows를 재부팅합니다.

Docker Desktop을 실행한 뒤 왼쪽 아래가 `Engine running`이 될 때까지 기다립니다.

확인:

```powershell
docker version
docker compose version
git --version
py --version
```

## 3-1. 빠른 설치

이미 Git/Python/Docker가 설치되어 있으면 아래만 실행해도 됩니다.

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\robot-controller-setup.ps1
```

평소 실행은 아래 한 줄입니다.

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\robot-controller-start.ps1
```

더 쉬운 방법:

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\setup_robot_controller.bat
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\start_robot_controller.bat
```

## 4. 프로젝트 다운로드

일반 PowerShell을 열고 그대로 붙여넣습니다.

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
```

이미 폴더가 있으면 업데이트만 합니다.

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
git pull
```

## 5. MySQL 준비

MySQL이 이 Robot Controller PC에 설치되어 있고, 이 PC의 IPv4가 `192.168.3.141`인 기준입니다.

MySQL 접속:

```powershell
mysql -u root -p
```

비밀번호를 입력한 뒤 아래 SQL을 그대로 붙여넣습니다.

```sql
CREATE DATABASE IF NOT EXISTS faictory_mes
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'guest'@'%' IDENTIFIED BY 'guest1234';
GRANT ALL PRIVILEGES ON faictory_mes.* TO 'guest'@'%';
FLUSH PRIVILEGES;
```

Windows 방화벽에서 MySQL 포트를 열어줍니다. 관리자 PowerShell에서 실행합니다.

```powershell
New-NetFirewallRule -DisplayName "MySQL 3306 Inbound" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3306
```

접속 확인:

```powershell
Test-NetConnection 192.168.3.141 -Port 3306
```

`TcpTestSucceeded : True`가 나오면 네트워크 포트는 열린 상태입니다.

## 6. Docker 백엔드 설정

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
copy .env.example .env
notepad .env
```

`.env`에서 아래 값이 맞는지 확인합니다.

```env
ROBOT_A_IP=192.168.3.7
ROBOT_B_IP=192.168.3.6
ROBOT_C_IP=192.168.3.5
ROBOT_A_PLC_IP=192.168.3.150
ROBOT_B_PLC_IP=192.168.3.140
ROBOT_C_PLC_IP=192.168.3.120
ROBOT_AUTOCONNECT=0
ROBOT_CONTROL_MODE=auto
HMI_MQTT_AUTOCONNECT=1
FACTORY_ORCHESTRATOR_AUTOSTART=0

MYSQL_HOST=192.168.3.141
MYSQL_PORT=3306
MYSQL_USER=guest
MYSQL_PASSWORD=guest1234
MYSQL_DATABASE=faictory_mes

PLC_PROCESS_IP=192.168.3.150
PLC_PROCESS_PORT=2000
PLC_MONITOR_IP=192.168.3.160
PLC_MONITOR_PORT=2000

PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
```

기본값은 무연결 시작입니다. `ROBOT_AUTOCONNECT=0`이면 Docker Robot Controller가 켜져도 로봇 소켓을 바로 잡지 않고, UI에서 연결을 눌렀을 때 접속합니다. `FACTORY_ORCHESTRATOR_AUTOSTART=0`이면 오래된 PLC/MES 루프가 프로그램 시작과 동시에 하드웨어에 붙지 않습니다.

## 7. Docker 서비스 실행

처음 실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose build
docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
```

평소 실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
```

상태 확인:

```powershell
docker compose ps
```

정상이라면 아래 컨테이너가 `Up`입니다.

```text
indy7_mqtt_broker
indy7_db_worker
indy7_digital_twin
indy7_robot_controller
indy7_plc_bridge
```

로그 확인:

```powershell
docker compose logs -f robot_controller
```

다른 터미널에서:

```powershell
docker compose logs -f plc_bridge db_worker
```

## 8. HMI UI 실행

처음 1회:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

만약 가상환경 실행이 막히면 한 번만 실행합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

운영 실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
.\.venv\Scripts\Activate.ps1
$env:ROBOT_CONTROL_MODE="mqtt"
python frontend\run_ui_only.py
```

## 9. 통신 확인 명령

Robot:

```powershell
Test-NetConnection 192.168.3.7 -Port 6066
Test-NetConnection 192.168.3.6 -Port 6066
Test-NetConnection 192.168.3.5 -Port 6066
```

PLC:

```powershell
Test-NetConnection 192.168.3.150 -Port 2000
Test-NetConnection 192.168.3.160 -Port 2000
```

MySQL:

```powershell
Test-NetConnection 192.168.3.141 -Port 3306
```

Docker:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose ps
docker stats --no-stream
```

## 10. 종료와 재시작

UI 종료:

```text
HMI 창을 닫습니다.
```

Docker 백엔드 종료:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose down
```

Docker 백엔드 재시작:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean\backend
docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
```

## 11. 운영 원칙

생산 모드:

```text
PLC가 메인 제어권을 가집니다.
Robot은 PLC Y160 -> Robot DI0 물리 배선을 보고 시작합니다.
Robot Controller PC는 상태 수집, HMI, 3D 동기화, DB 저장을 담당합니다.
```

티칭/점검 모드:

```text
HMI에서 선택한 Robot에 직접 명령을 보낼 수 있습니다.
이때 PLC 자동 시작 신호와 동시에 제어하지 않도록 현장 인터락을 확인해야 합니다.
```
