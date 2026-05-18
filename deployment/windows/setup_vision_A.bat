@echo off
setlocal
cd /d "%~dp0..\.."
powershell -ExecutionPolicy Bypass -File ".\deployment\windows\vision-pc-setup.ps1" -Role A
pause
