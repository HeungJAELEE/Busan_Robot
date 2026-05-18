param(
    [string]$ProjectRoot = "",
    [switch]$NoUi
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
}

$BackendDir = Join-Path $ProjectRoot "backend"
Set-Location $BackendDir

docker compose up -d message_broker db_worker digital_twin robot_controller plc_bridge
docker compose ps

if (-not $NoUi) {
    Set-Location $ProjectRoot
    $env:ROBOT_CONTROL_MODE = "mqtt"
    $env:FACTORY_ORCHESTRATOR_AUTOSTART = "0"
    $env:FACTORY_ORCHESTRATOR_SIMULATION = "0"
    & ".\.venv\Scripts\python.exe" "frontend\run_ui_only.py"
}
