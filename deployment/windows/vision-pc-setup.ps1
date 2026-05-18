param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("A", "B", "C")]
    [string]$Role,

    [string]$InstallRoot = "C:\Busan_Project",
    [string]$DbHost = "192.168.3.141",
    [string]$DbUser = "guest",
    [string]$DbPassword = "guest1234",
    [string]$DbName = "faictory_mes",
    [int]$CameraIndex = -1
)

$ErrorActionPreference = "Stop"

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name command not found. $InstallHint"
    }
}

Write-Host "== Vision PC setup: Process $Role =="
Write-Host "This PC installs Vision only. It does not install Robot Controller, HMI, or Docker services."

Require-Command "git" "Install Git for Windows first: winget install --id Git.Git -e"
Require-Command "py" "Install Python 3.11 first: winget install --id Python.Python.3.11 -e"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$VisionRepo = Join-Path $InstallRoot "factory_mes"

if (-not (Test-Path $VisionRepo)) {
    git clone https://github.com/youngjinsgithub/factory_mes.git $VisionRepo
}

Set-Location $VisionRepo
git pull

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install opencv-python pymysql pymcprotocol ultralytics torch torchvision torchaudio

$ScriptByRole = @{
    "A" = "mes\A_Process_pendant.py"
    "B" = "mes\B_Process_pendant.py"
    "C" = "mes\C_Process_pendant.py"
}

$TargetScript = Join-Path $VisionRepo $ScriptByRole[$Role]

if (-not (Test-Path $TargetScript)) {
    throw "Vision script not found: $TargetScript"
}

$content = Get-Content $TargetScript -Raw
$content = $content -replace "'host':\s*'[^']*'", "'host': '$DbHost'"
$content = $content -replace "'user':\s*'[^']*'", "'user': '$DbUser'"
$content = $content -replace "'password':\s*'[^']*'", "'password': '$DbPassword'"
$content = $content -replace "'db':\s*'[^']*'", "'db': '$DbName'"

if ($CameraIndex -ge 0) {
    $content = $content -replace "CAMERA_INDEX\s*=\s*\d+", "CAMERA_INDEX = $CameraIndex"
}

Set-Content -Path $TargetScript -Value $content -Encoding UTF8

$RunnerPath = Join-Path $VisionRepo "run_vision_$Role.bat"
$Runner = @"
@echo off
cd /d $VisionRepo
call .venv\Scripts\activate.bat
python $($ScriptByRole[$Role])
pause
"@
Set-Content -Path $RunnerPath -Value $Runner -Encoding ASCII

Write-Host ""
Write-Host "Vision PC $Role setup complete."
Write-Host "Run file:"
Write-Host "  $RunnerPath"

if ($Role -eq "B" -or $Role -eq "C") {
    $ModelPath = Join-Path $VisionRepo "C_VISION.pt"
    if (-not (Test-Path $ModelPath)) {
        Write-Host ""
        Write-Host "WARNING: C_VISION.pt was not found."
        Write-Host "Copy your YOLO model to:"
        Write-Host "  $ModelPath"
    }
}
