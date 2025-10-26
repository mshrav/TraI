from gui import TradingBotGUI
import tkinter as tk
import sys
import argparse

def run_gui():
    """Run the GUI version of the trading bot."""
    print("🤖 AI Trading Bot - GUI Mode")
    print("=" * 40)
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()

def run_telegram():
    """Run the Telegram bot version."""
    print("🤖 AI Trading Bot - Telegram Mode")
    print("=" * 40)
    from run_telegram_bot import main as telegram_main
    telegram_main()

def main():
    """Main entry point with mode selection."""
    parser = argparse.ArgumentParser(description="AI Trading Bot")
    parser.add_argument(
        "--mode",
        choices=["gui", "telegram"],
        default="gui",
        help="Choose the interface mode (default: gui)"
    )

    args = parser.parse_args()

    if args.mode == "telegram":
        run_telegram()
    else:
        run_gui()

if __name__ == "__main__":
    main()
