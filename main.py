"""TraI entry point: desktop GUI, local admin dashboard, or Telegram bot."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="TraI - AI stock analysis and paper-trading assistant")
    parser.add_argument("--mode", choices=["gui", "dashboard", "telegram"], default="dashboard")
    args = parser.parse_args()

    if args.mode == "gui":
        import tkinter as tk
        from gui import TradingBotGUI
        root = tk.Tk()
        TradingBotGUI(root)
        root.mainloop()
    elif args.mode == "dashboard":
        from dashboard_server import run_server
        run_server()
    else:
        from run_telegram_bot import main as run_bot
        run_bot()


if __name__ == "__main__":
    main()
