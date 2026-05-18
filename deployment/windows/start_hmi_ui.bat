@echo off
setlocal
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\deployment\windows\start-hmi-ui.ps1"
pause
