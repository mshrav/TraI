# TraI — AI Stock Analysis & Telegram Dashboard

TraI is a **research and paper-analysis project** for historical stock data. It combines a Python stock-analysis engine, RSI/MACD/moving-average signals, a next-session close regression baseline, a local Flask/Socket.IO admin inbox, and an optional Telegram bot.

> **Important:** This project does not place real trades. Yahoo Finance data is unofficial, can be delayed or unavailable, and is not an exchange-grade feed. Prediction outputs and technical signals are experimental and are not investment advice. The reported signal score is a rule score, **not** a probability of profit.

## Security before first run

The source archive supplied for this cleanup included a Telegram bot token and real Telegram user profile records. They have been removed from this cleaned package. **Revoke the previously exposed bot token in Telegram's @BotFather and generate a new token.** Treat the old token as compromised even if you believe it was only used locally.

1. Copy `.env.example` to `.env` (Windows setup does this automatically).
2. Paste the newly generated token into `TELEGRAM_BOT_TOKEN=`.
3. Replace `DASHBOARD_WEBHOOK_TOKEN` and `FLASK_SECRET_KEY` with long random values.
4. Never upload `.env`, `user_data.json`, or `messages.json` to GitHub.

The dashboard binds to `127.0.0.1` by default. It currently has **no admin login**, so do not set `DASHBOARD_HOST=0.0.0.0` or expose it through a public tunnel/reverse proxy. Public deployment requires authentication, authorization, HTTPS, rate limiting, and a production WSGI/Socket.IO server first.

## Requirements

- Windows 10/11 (instructions below)
- Python **3.11** recommended
- Internet access for pip installation and Yahoo Finance data
- Telegram account and a bot token only if you want Telegram functionality
- VS Code optional

## Windows installation

1. Install Python 3.11 from <https://www.python.org/downloads/>. In the installer, enable **Add Python to PATH** and the Python Launcher.
2. Extract the ZIP into a normal folder, for example `C:\Projects\TraI`. Do not run it from inside the ZIP preview.
3. Open that extracted folder in VS Code (`File → Open Folder`).
4. Double-click `setup.bat`, or open a terminal in the folder and run:

   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements-dev.txt
   copy .env.example .env
   ```

5. Open `.env` in VS Code. Add your **new** Telegram token. Set your own random `DASHBOARD_WEBHOOK_TOKEN` and `FLASK_SECRET_KEY` values. Save the file.

If PowerShell blocks activation, you can skip activation and call `.venv\Scripts\python.exe` directly, as the batch files do.

## Start TraI

### Start both dashboard and Telegram bot

Double-click `run_all.bat`. It opens the dashboard in a separate console and runs the Telegram bot in the current console. The bot token must be configured to start the Telegram bot.

### Start only the web dashboard

Double-click `run_dashboard.bat`, then open <http://127.0.0.1:5000> in Chrome or Edge. Check <http://127.0.0.1:5000/healthz> for the local health response.

The dashboard can start without a Telegram token, but the **Send** action will be disabled by the server until a token is configured.

### Start only the Telegram bot

Double-click `run_telegram_bot.bat` or run:

```powershell
.venv\Scripts\python.exe run_telegram_bot.py
```

Open your bot in Telegram and send `/start`. Complete the profile flow, then try `/help`, `/analyze RELIANCE.NS`, `/watchlist`, or `/recommend`.

### Start the desktop GUI

Double-click `run_gui.bat` or run:

```powershell
.venv\Scripts\python.exe main.py --mode gui
```

The web dashboard is the Telegram admin inbox; the Tkinter GUI is a separate basic stock-prediction interface.

## Useful commands

```powershell
# Syntax check
.venv\Scripts\python.exe -m compileall -q .

# Automated tests
.venv\Scripts\python.exe -m pytest -v

# Or run syntax, tests and installation smoke checks together (Windows)
run_checks.bat

# Coverage report
.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing

# Run one component directly
.venv\Scripts\python.exe main.py --mode dashboard
.venv\Scripts\python.exe main.py --mode telegram
```

## Dashboard behaviour

- Telegram user messages are posted to the local dashboard webhook and saved to `messages.json`.
- The browser receives updates through Socket.IO, with HTTP polling as a fallback.
- Admin replies are sent synchronously through Telegram. A reply appears as delivered only after Telegram accepts it; failed sends return an error and are not recorded as delivered.
- If the dashboard is offline, the bot writes incoming messages to the local JSON fallback store; restart the dashboard to view them.

## Project layout

```text
TraI/
├── dashboard_server.py       # Local Flask + Socket.IO admin dashboard
├── telegram_bot.py           # Telegram bot handlers
├── run_telegram_bot.py       # Telegram configuration/launcher
├── data_fetcher.py           # Yahoo Finance OHLCV ingestion/validation
├── model_trainer.py          # Chronological holdout evaluation + regression
├── trading_strategy.py       # RSI, MACD, moving averages and rule signals
├── user_manager.py           # Local user profile/watchlist store
├── gui.py                    # Tkinter stock-analysis GUI
├── templates/dashboard.html
├── static/css/style.css
├── static/js/dashboard.js
├── tests/                    # Automated regression tests
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── setup.bat / run_*.bat
```

## Known limitations / next improvements

- JSON persistence is suitable only for a local demo/single-instance run. Move to SQLite/PostgreSQL before multi-user or cloud deployment.
- The dashboard has no authentication and must remain localhost-only.
- Telegram delivery and live market data require valid credentials/network access and cannot be validated by offline unit tests.
- The regression model uses a small set of OHLCV features and is a baseline, not a validated trading edge. Add walk-forward evaluation, transaction-cost-aware backtesting, benchmark comparisons, and out-of-sample reporting before making performance claims.
- The project is **paper/research only**. No broker integration or live order execution is included.

## Troubleshooting

- **`ModuleNotFoundError`**: rerun `setup.bat`; make sure you use `.venv\Scripts\python.exe`, not another Python installation.
- **`TELEGRAM_BOT_TOKEN is not configured`**: edit `.env`; confirm the filename is `.env`, not `.env.txt`.
- **Telegram `Unauthorized`**: revoke the exposed token with @BotFather and use the newly generated token.
- **No stock data**: verify the ticker (`RELIANCE.NS`, `TCS.NS`), internet access, and Yahoo Finance availability. Try again later if rate-limited.
- **Dashboard page opens but is empty**: check the dashboard console, `/healthz`, and browser developer console. Socket.IO uses an external CDN; HTTP polling still refreshes the dashboard if Socket.IO is unavailable.
- **Admin reply fails**: confirm the bot has already received `/start` from that user, the token is valid, and the dashboard can reach Telegram. A failed delivery is reported rather than being marked as sent.
- **Port 5000 already in use**: change `DASHBOARD_PORT` in `.env` and open the matching localhost URL.

## License

Add a license before accepting outside contributions or distributing this project. Check the licences and terms of every dependency and data source before commercial use.
