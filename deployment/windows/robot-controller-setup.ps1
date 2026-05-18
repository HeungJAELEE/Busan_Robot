param(
    [string]$ProjectRoot = "",
    [string]$MysqlHost = "192.168.3.141",
    [string]$MysqlUser = "guest",
    [string]$MysqlPassword = "guest1234",
    [string]$MysqlDatabase = "faictory_mes",
    [string]$RobotAIp = "192.168.3.7",
    [string]$RobotBIp = "192.168.3.6",
    [string]$RobotCIp = "192.168.3.5",
    [string]$PlcProcessIp = "192.168.3.150",
    [string]$PlcMonitorIp = "192.168.3.160"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
}

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name command not found. $InstallHint"
    }
}

Write-Host "== Robot Controller PC setup =="
Require-Command "git" "Install Git for Windows first: winget install --id Git.Git -e"
Require-Command "py" "Install Python 3.11 first: winget install --id Python.Python.3.11 -e"
Require-Command "docker" "Install and start Docker Desktop first: winget install --id Docker.DockerDesktop -e"

if (-not (Test-Path $ProjectRoot)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ProjectRoot) | Out-Null
    git clone https://github.com/HeungJAELEE/Busan_Robot.git $ProjectRoot
}

Set-Location $ProjectRoot
git pull

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

$BackendDir = Join-Path $ProjectRoot "backend"
Set-Location $BackendDir

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$envText = @"
# Indy7 HMI Docker deployment settings
MQTT_PORT=1883
MQTT_WS_PORT=9001
IMAGE_TAG=latest

ROBOT_A_IP=$RobotAIp
ROBOT_B_IP=$RobotBIp
ROBOT_C_IP=$RobotCIp
ROBOT_A_PLC_IP=$PlcProcessIp
ROBOT_B_PLC_IP=192.168.3.140
ROBOT_C_PLC_IP=192.168.3.120
ROBOT_NAME=NRMK-Indy7
ROBOT_MODEL=NRMK-Indy7
DEFAULT_ROBOT_ID=Robot A
ROBOT_AUTOCONNECT=0
ROBOT_CONTROL_MODE=auto
HMI_MQTT_AUTOCONNECT=1
FACTORY_ORCHESTRATOR_AUTOSTART=0
FACTORY_ORCHESTRATOR_SIMULATION=0

DIGITAL_TWIN_PORT=8080

PLC_IP=$PlcProcessIp
PLC_PORT=2000
PLC_PROCESS_IP=$PlcProcessIp
PLC_PROCESS_PORT=2000
PLC_MONITOR_IP=$PlcMonitorIp
PLC_MONITOR_PORT=2000
PLC_SCAN_INTERVAL_SEC=0.1
PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
PLC_CYCLE_START_DEVICE=X11
PLC_ROBOT_BUSY_DEVICE=M200
PLC_CYCLE_COMPLETE_DEVICE=M101
PLC_ACK_DEVICE=M105
PLC_ALARM_DEVICE=M102

MYSQL_HOST=$MysqlHost
MYSQL_PORT=3306
MYSQL_USER=$MysqlUser
MYSQL_PASSWORD=$MysqlPassword
MYSQL_DATABASE=$MysqlDatabase

CAMERA_DEVICE=/dev/video0
"@

Set-Content -Path ".env" -Value $envText -Encoding UTF8

docker compose build
docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
docker compose ps

Write-Host ""
Write-Host "Robot Controller PC setup complete."
Write-Host "Start UI with:"
Write-Host "  cd $ProjectRoot"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  `$env:ROBOT_CONTROL_MODE='mqtt'"
Write-Host "  python frontend\run_ui_only.py"
