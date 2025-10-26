@echo off
echo ========================================
echo 🤖 AI Trading Bot Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python detected
echo.

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed
echo.

REM Create config file if it doesn't exist
if not exist "bot_config.json" (
    echo 📝 Creating configuration template...
    echo {"telegram_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE", "admin_user_ids": [], "max_stocks_per_user": 5, "default_risk_level": "medium", "supported_exchanges": ["NSE", "BSE", "NASDAQ", "NYSE"], "analysis_timeframe": "1y", "prediction_days": 1} > bot_config.json
    echo ✅ Configuration template created
) else (
    echo ✅ Configuration file already exists
)
echo.

REM Create user data file if it doesn't exist
if not exist "user_data.json" (
    echo 📝 Creating user data file...
    echo {} > user_data.json
    echo ✅ User data file created
) else (
    echo ✅ User data file already exists
)
echo.

echo 🎉 Setup completed successfully!
echo.
echo Next steps:
echo 1. Edit bot_config.json with your Telegram bot token
echo 2. Run: python main.py --mode telegram
echo 3. Or double-click run_telegram_bot.bat
echo.
echo For help, see README.md
echo.

pause
