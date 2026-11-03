#!/usr/bin/env python3
"""Start the Telegram bot after validating local configuration."""
from settings import get_telegram_token
from telegram_bot import TelegramTradingBot


def main():
    token = get_telegram_token()
    if not token:
        raise SystemExit(
            "Telegram token is not configured. Create .env from .env.example "
            "and set TELEGRAM_BOT_TOKEN. Revoke any token previously shared publicly."
        )
    print("Starting TraI Telegram bot. Press Ctrl+C to stop.")
    TelegramTradingBot(token).run()


if __name__ == "__main__":
    main()
