@echo off
setlocal
cd /d "%~dp0..\.."
powershell -ExecutionPolicy Bypass -File ".\deployment\windows\vision-pc-start.ps1" -Role B
pause
