param(
    [switch]$Registry,
    [switch]$Pull,
    [switch]$Build,
    [switch]$Robot,
    [switch]$Plc,
    [switch]$Vision
)

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path -Parent $PSScriptRoot
Set-Location $BackendDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Install and start Docker Desktop for Windows first."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Check robot, PLC, and MySQL IP settings before production use."
}

$composeFileArgs = @()
if ($Registry) {
    $composeFileArgs = @("-f", "docker-compose.registry.yml")
}

if ($Build -and -not $Registry) {
    & docker compose @composeFileArgs build
}

if ($Pull -and $Registry) {
    & docker compose @composeFileArgs pull
}

& docker compose @composeFileArgs up -d message_broker db_worker digital_twin

$services = @()
if ($Robot) {
    $services += "robot_controller"
}
if ($Plc) {
    $services += "plc_bridge"
}
if ($services.Count -gt 0) {
    & docker compose @composeFileArgs up -d @services
}

if ($Vision) {
    & docker compose @composeFileArgs --profile vision up -d vision_yolo
}

& docker compose @composeFileArgs ps
