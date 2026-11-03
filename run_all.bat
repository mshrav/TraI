@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
start "TraI Dashboard" "%~dp0.venv\Scripts\python.exe" "%~dp0dashboard_server.py"
timeout /t 3 /nobreak >nul
".venv\Scripts\python.exe" run_telegram_bot.py
pause
