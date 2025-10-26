@echo off
echo ================================================
echo 🤖 AI Trading Bot - Telegram Interface
echo ⚠️  PAPER TRADING ONLY - Educational Purposes
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "telegram_bot.py" (
    echo ❌ telegram_bot.py not found in current directory
    echo Please run this from the AI_Trading_Bot directory
    pause
    exit /b 1
)

REM Check if config file exists
if not exist "bot_config.json" (
    echo ❌ bot_config.json not found!
    echo Creating template config file...
    echo {"telegram_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE", "admin_user_ids": [], "max_stocks_per_user": 5, "default_risk_level": "medium", "supported_exchanges": ["NSE", "BSE", "NASDAQ", "NYSE"], "analysis_timeframe": "1y", "prediction_days": 1} > bot_config.json
    echo.
    echo 📝 Template bot_config.json created!
    echo Please edit bot_config.json and add your Telegram bot token.
    echo Get your token from @BotFather on Telegram.
    echo.
    pause
    exit /b 1
)

echo ✅ Starting AI Trading Bot...
echo ⚠️  This bot provides educational analysis only - no real trades executed
echo Press Ctrl+C to stop the bot
echo.

python run_telegram_bot.py

pause
