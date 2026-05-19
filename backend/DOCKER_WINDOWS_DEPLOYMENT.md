# Windows Docker Deployment Guide

Windows 현장 PC에서는 Docker Desktop + WSL2 기반으로 Indy7 HMI 백엔드 컨테이너를 실행합니다.

> `wsl` 명령은 Windows 전용입니다. Mac 터미널에서는 `zsh: command not found: wsl`이 정상입니다.

## 1. Windows 준비

관리자 권한 PowerShell을 열고 WSL2를 설치합니다.

```powershell
wsl --install
```

설치 후 Windows를 재부팅합니다.

Docker Desktop for Windows를 설치합니다.

- 설치 옵션에서 `Use WSL 2 instead of Hyper-V`를 선택합니다.
- 설치 후 Docker Desktop을 실행하고 Engine running 상태를 기다립니다.

확인:

```powershell
docker version
docker compose version
```

## 2. 프로젝트 위치

예시:

```powershell
cd C:\Users\leejaeheung\Documents\Busan_Project\Indy7_HMI_Clean\backend
copy .env.example .env
notepad .env
```

`.env`에서 현장 IP를 직접 입력합니다. `<...>` 표시는 그대로 쓰지 말고 현장 값으로 바꾸는 자리입니다.

```env
ROBOT_A_IP=<Robot_A_IP>
ROBOT_B_IP=<Robot_B_IP>
ROBOT_C_IP=<Robot_C_IP>
MYSQL_HOST=<MySQL_PC_IP>
PLC_IP=<PLC_PROCESS_IP>
PLC_PORT=2000
PLC_MONITOR_IP=<PLC_MONITOR_IP>
PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
```

## 3. 업로드된 이미지로 실행

GitHub Container Registry에 업로드된 `linux/amd64` 이미지를 받아 실행하는 방식입니다. Windows 현장 PC에는 이 방식이 가장 편합니다.

```powershell
docker compose -f docker-compose.registry.yml pull
docker compose -f docker-compose.registry.yml up -d message_broker db_worker digital_twin
```

Page 1 웹 모니터 확인:

```powershell
# 로봇 컨트롤러 PC 자체에서
start http://localhost:8080

# 다른 PC/태블릿에서 볼 때
# 1) 로봇 컨트롤러 PC의 IPv4 확인
ipconfig

# 2) 브라우저 주소창에 입력
# http://<로봇컨트롤러_PC_IP>:8080
```

실제 로봇/PLC까지 붙일 때:

```powershell
docker compose -f docker-compose.registry.yml up -d robot_controller plc_bridge
```

상태 확인:

```powershell
docker compose -f docker-compose.registry.yml ps
docker compose -f docker-compose.registry.yml logs -f robot_controller
```

종료:

```powershell
docker compose -f docker-compose.registry.yml down
```

## 4. 소스에서 직접 빌드

현장 PC에서 직접 빌드할 수도 있습니다.

```powershell
docker compose build
docker compose up -d message_broker db_worker digital_twin
docker compose up -d robot_controller plc_bridge
```

## 5. PowerShell 스크립트 실행

기본 인프라만 실행:

```powershell
.\scripts\windows-start.ps1 -Registry -Pull
```

로봇/PLC까지 실행:

```powershell
.\scripts\windows-start.ps1 -Registry -Pull -Robot -Plc
```

UI가 Docker Robot Controller를 통해 로봇을 제어하도록 하려면 UI 실행 전에 아래 값을 설정합니다.

```powershell
$env:ROBOT_CONTROL_MODE="mqtt"
```

소스에서 직접 빌드 후 실행:

```powershell
.\scripts\windows-start.ps1 -Build -Robot -Plc
```

## 6. 주의사항

- Windows PC가 `.env`에 입력한 로봇/PLC/MySQL 네트워크에 실제로 접근 가능해야 합니다.
- 방화벽에서 Docker Desktop, Python/HMI, MQTT `1883`, Digital Twin `8080` 포트가 막히지 않아야 합니다.
- 내부망 다른 PC에서 Page 1 웹 모니터가 안 열리면 Windows Defender 방화벽에서 TCP `8080` 인바운드를 허용합니다.
- `vision_yolo`의 USB 카메라는 Linux `/dev/video0` 기준이라 Windows에서는 별도 카메라 연동 방식이 필요합니다.
- 로봇 실장 전에는 먼저 `message_broker`, `db_worker`, `digital_twin`만 실행해서 Docker와 DB/MQTT 흐름을 확인합니다.
