#!/usr/bin/env python3
"""
AI Trading Bot - Telegram Interface
Easy-to-run entry point for the Telegram bot
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot import TelegramTradingBot
import json

def main():
    """Main entry point for the Telegram bot."""
    print("🤖 AI Trading Bot - Telegram Interface")
    print("=" * 50)

    # Check if config file exists
    config_file = "bot_config.json"
    if not os.path.exists(config_file):
        print(f"❌ Configuration file '{config_file}' not found!")
        print("Please create bot_config.json with your Telegram bot token.")
        print("Get your token from @BotFather on Telegram.")
        return

    # Load configuration
    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        token = config.get("telegram_token")
        if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            print("❌ Please set your Telegram bot token in bot_config.json")
            print("Get your token from @BotFather on Telegram")
            print("\nExample bot_config.json:")
            print('{"telegram_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"}')
            return

        print("✅ Configuration loaded successfully")
        print("🚀 Starting Telegram bot...")

        # Create and run bot
        bot = TelegramTradingBot(token)
        bot.run()

    except json.JSONDecodeError:
        print("❌ Invalid JSON in bot_config.json")
        return
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return

if __name__ == "__main__":
    main()
