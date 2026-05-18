param(
    [string]$ProjectRoot = "C:\Busan_Project\Indy7_HMI_Clean",
    [switch]$NoUi
)

$ErrorActionPreference = "Stop"

$BackendDir = Join-Path $ProjectRoot "backend"
Set-Location $BackendDir

docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
docker compose ps

if (-not $NoUi) {
    Set-Location $ProjectRoot
    $env:ROBOT_CONTROL_MODE = "mqtt"
    & ".\.venv\Scripts\python.exe" "frontend\run_ui_only.py"
}
