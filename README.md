# AI Trading Bot

A comprehensive AI-powered trading bot for stock analysis and trading recommendations. Features both GUI and Telegram interfaces for easy access. Built with Python, yfinance for data, scikit-learn for ML, and technical analysis.

## Features

### 🤖 Core Features
- **Stock Analysis**: Analyze any stock with AI predictions and technical indicators
- **Trading Signals**: Get buy/sell/hold recommendations with confidence levels
- **Portfolio Management**: Personalized recommendations based on risk tolerance
- **Watchlist Management**: Track your favorite stocks
- **User Profiles**: Personalized experience with risk assessment

### 💻 Interface Options
- **GUI Mode**: Traditional desktop application with tkinter
- **Telegram Bot**: Chat-based interface for mobile/convenient access

### 📊 Technical Analysis
- Linear regression predictions
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Moving averages (20-day, 50-day)
- Risk-based stock recommendations

## Requirements
- Python 3.7+
- Windows 10/11 (or any OS with Python installed)
- Telegram account (for Telegram bot mode)
- Internet connection for stock data

## Setup

### Quick Setup (Recommended)
Run the automated setup script:
- **Windows**: Double-click `setup.bat`
- **Command Line**: `python setup.py`

This will automatically:
- Check Python version
- Install dependencies
- Create configuration files
- Set up user data storage

### Manual Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Choose Your Interface

#### Option A: GUI Mode (Desktop Application)
```bash
python main.py
```

#### Option B: Telegram Bot Mode
1. **Create a Telegram Bot**:
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token you receive

2. **Configure the Bot**:
   - Edit `bot_config.json`
   - Replace `YOUR_TELEGRAM_BOT_TOKEN_HERE` with your actual token

3. **Run the Bot**:
   - **Easy Way (Windows)**: Double-click `run_telegram_bot.bat`
   - **Command Line**: `python run_telegram_bot.py`
   - **Python Mode**: `python main.py --mode telegram`

## Usage

### GUI Mode
1. Run `python main.py`
2. Enter a stock symbol (e.g., RELIANCE.NS)
3. Click "Fetch Data" to get historical data
4. Click "Train Model" to train the AI model
5. Click "Predict Next Price" to get predictions

### Telegram Bot Mode
1. Start the bot and message `/start`
2. Complete your profile (name, email, risk tolerance, goals)
3. Use commands:
   - `/analyze RELIANCE.NS` - Analyze a specific stock
   - `/recommend` - Get personalized recommendations
   - `/watchlist` - View your stock watchlist
   - `/profile` - View/edit your profile
   - `/help` - Show all commands

## Stock Symbols
- **Indian Stocks**: Add `.NS` suffix (e.g., RELIANCE.NS, TCS.NS)
- **US Stocks**: Use standard symbols (e.g., AAPL, GOOGL)
- **Examples**: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and set up your profile |
| `/profile` | View your profile and stats |
| `/analyze <symbol>` | Analyze a specific stock |
| `/recommend` | Get personalized stock recommendations |
| `/watchlist` | View your stock watchlist |
| `/status` | Check bot status |
| `/help` | Show help message |

## Risk Levels
- **🛡️ Low Risk**: Blue-chip stocks, stable companies
- **⚖️ Medium Risk**: Balanced growth and stability
- **🎲 High Risk**: Growth stocks, higher volatility

## Important Notes

### 🚨 **PAPER TRADING ONLY**
- **⚠️ NO REAL TRADING**: This bot provides analysis and recommendations ONLY
- **📊 VIRTUAL TRADING**: All trading suggestions are for educational purposes
- **💰 NO EXECUTION**: The bot cannot place actual orders or execute trades
- **🎓 EDUCATIONAL TOOL**: Designed for learning technical analysis and trading concepts

### ⚠️ **Risk Disclaimer**
- **Trading involves risk**: Predictions are based on historical data and not guaranteed to be accurate
- **Not financial advice**: Use for learning and research purposes only
- **Past performance ≠ future results**: Historical data doesn't guarantee future outcomes
- **Do your own research**: Always verify information before making investment decisions

### 🔒 **Security & Privacy**
- **Bot Token**: Keep your Telegram bot token secure and don't share it
- **User Data**: All user data is stored locally in JSON files
- **No External APIs**: No third-party trading platforms connected

### 🌐 **Technical Requirements**
- **Internet Required**: Active internet connection needed for stock data
- **Data Sources**: Uses Yahoo Finance (yfinance) for historical data
- **No Real-time Data**: Analysis based on end-of-day data

## Troubleshooting

### GUI Issues
- Ensure tkinter is properly installed
- Try running as administrator

### Telegram Bot Issues
- Verify your bot token in `bot_config.json`
- Check if bot is properly created with @BotFather
- Ensure bot is not already running elsewhere

### Data Fetching Issues
- Check internet connection
- Verify stock symbol format
- Some symbols may not be available in all regions

## Contributing
Feel free to contribute improvements or report issues!

## License
This project is for educational purposes only.
