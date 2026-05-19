param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
}

Set-Location $ProjectRoot

$env:FACTORY_ORCHESTRATOR_AUTOSTART = "0"
$env:FACTORY_ORCHESTRATOR_SIMULATION = "0"
$env:HMI_MQTT_AUTOCONNECT = "0"
if ([string]::IsNullOrWhiteSpace($env:ROBOT_CONTROL_MODE)) {
    $env:ROBOT_CONTROL_MODE = "mqtt"
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython "frontend\run_ui_only.py"
    exit $LASTEXITCODE
}

Write-Host "[WARN] .venv was not found. Falling back to system python."
python "frontend\run_ui_only.py"
