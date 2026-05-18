@echo off
setlocal
cd /d "%~dp0..\.."
powershell -ExecutionPolicy Bypass -File ".\deployment\windows\robot-controller-start.ps1"
pause
