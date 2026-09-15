@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [upgrade probe] listening... send messages in Feishu now. Ctrl+C to stop.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-upgrade.ps1" -Probe
echo.
echo [exit code %ERRORLEVEL%] press any key to close...
pause >nul