"""Centralised application configuration loaded from .env or environment variables."""
from __future__ import annotations
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def get_telegram_token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if token:
        return token
    config_path = ROOT / "bot_config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            return str(config.get("telegram_token") or "").strip()
        except (OSError, json.JSONDecodeError):
            return ""
    return ""


def data_path(filename: str) -> Path:
    """Resolve runtime data files beside the application, independent of CWD."""
    return ROOT / filename
