@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-upgrade.ps1" %*
echo.
echo [exit code %ERRORLEVEL%] press any key to close...
pause >nul