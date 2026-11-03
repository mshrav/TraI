# TraI cleanup — verification report

## Checks executed in the build environment

| Check | Result | Notes |
|---|---|---|
| Python compilation (`compileall`) | PASS | All Python files compiled successfully on Python 3.13.5. |
| Automated tests (`pytest`) | PASS | 19 passed, 1 skipped. |
| Data-fetcher tests | PASS | Yahoo Finance calls are mocked; no network call is made. |
| ML tests | PASS | Chronological holdout, prediction guardrails, finite outputs and small-data rejection. |
| Strategy tests | PASS | RSI bounds/flat-market handling, insufficient-data handling, signal shape and budget validation. |
| User-store tests | PASS | User creation, profile completion, watchlist and JSON persistence. |
| Dashboard integration tests | SKIPPED | Flask and Flask-SocketIO are not installed in this build environment. They are listed in `requirements.txt` and will run after `setup.bat` installs them. |
| JavaScript syntax (`node --check`) | PASS | Checked with Node.js 22.16.0. |
| Python AST parse | PASS | All project Python source files parse. |
| Live Yahoo Finance | NOT RUN | Build environment could not install yfinance and has no package-network access. Use `smoke_test.py --market-data` on your PC. |
| Live Telegram send/polling | NOT RUN | Requires the newly rotated bot token and a real Telegram chat. |
| Tkinter visual launch | NOT RUN | Requires a Windows desktop/display. |

## What this means

The core data-cleaning logic, ML pipeline, signal engine and JSON user persistence pass automated tests. The full dashboard and Telegram integrations were not executable in the build environment because their dependencies were unavailable and pip could not reach package indexes. Therefore this report does **not** certify live Telegram delivery, Yahoo Finance connectivity or a visual Windows GUI launch.

After installing on Windows, run `run_checks.bat` and then follow the README's live smoke-test instructions.
