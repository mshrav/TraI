#!/usr/bin/env python3
"""
AI Trading Bot Setup Script
Helps users set up the bot quickly
"""

import os
import json
import sys
import subprocess

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_dependencies():
    """Install required packages."""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_config_template():
    """Create bot_config.json if it doesn't exist."""
    config_file = "bot_config.json"

    if os.path.exists(config_file):
        print("✅ Configuration file already exists")
        return True

    print("📝 Creating configuration template...")
    template = {
        "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
        "admin_user_ids": [],
        "max_stocks_per_user": 5,
        "default_risk_level": "medium",
        "supported_exchanges": ["NSE", "BSE", "NASDAQ", "NYSE"],
        "analysis_timeframe": "1y",
        "prediction_days": 1
    }

    try:
        with open(config_file, 'w') as f:
            json.dump(template, f, indent=2)
        print("✅ Configuration template created")
        print("📝 Please edit bot_config.json and add your Telegram bot token")
        return True
    except Exception as e:
        print(f"❌ Failed to create config file: {e}")
        return False

def create_user_data_file():
    """Create user_data.json if it doesn't exist."""
    data_file = "user_data.json"

    if os.path.exists(data_file):
        print("✅ User data file already exists")
        return True

    print("📝 Creating user data file...")
    try:
        with open(data_file, 'w') as f:
            json.dump({}, f, indent=2)
        print("✅ User data file created")
        return True
    except Exception as e:
        print(f"❌ Failed to create user data file: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    modules = [
        "yfinance",
        "pandas",
        "numpy",
        "sklearn",
        "telegram",
        "matplotlib"
    ]

    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed.append(module)

    if failed:
        print(f"❌ Missing modules: {', '.join(failed)}")
        return False

    print("✅ All modules imported successfully")
    return True

def main():
    """Main setup function."""
    print("🤖 AI Trading Bot Setup")
    print("=" * 50)

    steps = [
        ("Check Python version", check_python_version),
        ("Install dependencies", install_dependencies),
        ("Create config template", create_config_template),
        ("Create user data file", create_user_data_file),
        ("Test imports", test_imports)
    ]

    success = True
    for step_name, step_func in steps:
        print(f"\n🔧 {step_name}...")
        if not step_func():
            success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit bot_config.json with your Telegram bot token")
        print("2. Run: python main.py --mode telegram")
        print("3. Or double-click run_telegram_bot.bat (Windows)")
    else:
        print("❌ Setup failed. Please check the errors above.")

    print("\nFor help, see README.md")
    return success

if __name__ == "__main__":
    main()
