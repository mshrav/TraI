"""Local installation smoke test. Run after setup.bat / dependency installation."""
from __future__ import annotations
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn",
    "yfinance": "yfinance", "flask": "Flask", "flask_socketio": "Flask-SocketIO",
    "telegram": "python-telegram-bot", "requests": "requests", "dotenv": "python-dotenv",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-data", action="store_true", help="Make a live 5-day Yahoo Finance request for RELIANCE.NS")
    parser.add_argument("--require-telegram-token", action="store_true", help="Fail unless TELEGRAM_BOT_TOKEN is configured")
    args = parser.parse_args()

    failures = []
    print(f"TraI smoke test | Python {sys.version.split()[0]}")
    if sys.version_info < (3, 11):
        failures.append("Python 3.11 or newer is required (3.11 recommended).")
    for module, package in REQUIRED.items():
        found = importlib.util.find_spec(module) is not None
        print(f"{'OK' if found else 'MISSING'}  {package}")
        if not found:
            failures.append(f"Missing dependency: {package}")

    expected = ["dashboard_server.py", "telegram_bot.py", "data_fetcher.py", "model_trainer.py",
                "trading_strategy.py", "templates/dashboard.html", "static/js/dashboard.js"]
    for relative in expected:
        exists = (ROOT / relative).is_file()
        print(f"{'OK' if exists else 'MISSING'}  {relative}")
        if not exists:
            failures.append(f"Missing project file: {relative}")

    if not failures:
        try:
            from dashboard_server import app
            response = app.test_client().get("/healthz")
            ok = response.status_code == 200 and response.get_json().get("status") == "ok"
            print(f"{'OK' if ok else 'FAIL'}  dashboard /healthz (HTTP {response.status_code})")
            if not ok:
                failures.append("Dashboard health endpoint failed")
        except Exception as exc:
            failures.append(f"Dashboard import/health check failed: {exc}")

        try:
            import numpy as np
            import pandas as pd
            from model_trainer import StockPricePredictor
            from trading_strategy import TradingStrategy
            close = 100 + np.arange(120) * 0.2 + np.sin(np.arange(120) / 4)
            data = pd.DataFrame({"Open": close - .1, "High": close + .8,
                                 "Low": close - .8, "Close": close,
                                 "Volume": 100000 + np.arange(120)})
            model = StockPricePredictor()
            metrics = model.train(data)
            prediction = model.predict_next_close(data.tail(1))
            signal = TradingStrategy().generate_signals(data)
            ok = np.isfinite(prediction) and prediction > 0 and metrics["test_rows"] > 0 and signal["signal"] in {"BUY", "SELL", "HOLD"}
            print(f"{'OK' if ok else 'FAIL'}  synthetic ML train/evaluate/predict + indicators")
            if not ok:
                failures.append("Synthetic model/strategy check failed")
        except Exception as exc:
            failures.append(f"Model/strategy smoke test failed: {exc}")

        try:
            from settings import get_telegram_token
            token_present = bool(get_telegram_token())
            print(f"{'OK' if token_present else 'WARN'}  Telegram token {'configured' if token_present else 'not configured (bot will not start)'}")
            if args.require_telegram_token and not token_present:
                failures.append("TELEGRAM_BOT_TOKEN is not configured")
        except Exception as exc:
            failures.append(f"Could not read local configuration: {exc}")

    if args.market_data and not failures:
        try:
            from data_fetcher import fetch_stock_data
            frame = fetch_stock_data("RELIANCE.NS", "5d")
            ok = not frame.empty
            print(f"{'OK' if ok else 'FAIL'}  live Yahoo Finance fetch ({len(frame)} rows)")
            if not ok:
                failures.append("Live market-data smoke test returned no rows")
        except Exception as exc:
            failures.append(f"Live market-data check failed: {exc}")

    if failures:
        print("\nSMOKE TEST FAILED:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("\nSMOKE TEST PASSED. Live Telegram delivery is not tested by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
