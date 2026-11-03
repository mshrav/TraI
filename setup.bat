@echo off
setlocal
cd /d "%~dp0"
echo =====================================
echo TraI - Windows setup
echo =====================================

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11 from https://www.python.org/downloads/
  echo During installation, enable the Python Launcher and Add Python to PATH.
  pause
  exit /b 1
)

py -3.11 --version
if errorlevel 1 (
  echo Python 3.11 is required. Install it, then rerun setup.bat.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto failed
)

echo Installing dependencies. This step needs internet access...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed

if not exist ".env" (
  copy .env.example .env >nul
  echo Created .env. Open it and set TELEGRAM_BOT_TOKEN if you want Telegram enabled.
)
if not exist "messages.json" echo {}>messages.json
if not exist "user_data.json" echo {}>user_data.json

echo.
echo Setup completed. Next:
echo 1. Edit .env and add your NEW Telegram token.
echo 2. Run run_dashboard.bat for the web dashboard.
echo 3. Run run_telegram_bot.bat for the Telegram bot.
echo 4. Run run_all.bat to start both.
echo.
pause
exit /b 0

:failed
echo.
echo Setup failed. Check internet access and Python 3.11 installation.
pause
exit /b 1
