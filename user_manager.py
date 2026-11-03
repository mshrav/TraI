"""Simple JSON-backed Telegram user store with atomic writes."""
from __future__ import annotations
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from settings import data_path


class UserManager:
    def __init__(self, data_file="user_data.json"):
        self.data_file = Path(data_file)
        if not self.data_file.is_absolute():
            self.data_file = data_path(str(self.data_file))
        self._lock = threading.RLock()
        self.users = self.load_users()

    def load_users(self) -> Dict:
        if not self.data_file.exists():
            return {}
        try:
            payload = json.loads(self.data_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            # Preserve the corrupt file for diagnosis; do not silently overwrite it.
            backup = self.data_file.with_suffix(self.data_file.suffix + ".corrupt")
            try:
                self.data_file.replace(backup)
            except OSError:
                pass
            return {}

    def save_users(self):
        with self._lock:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix="users-", suffix=".tmp", dir=self.data_file.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(self.users, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.data_file)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def register_user(self, user_id: int, username: str = None) -> Dict:
        key = str(int(user_id))
        with self._lock:
            if key in self.users:
                return self.users[key]
            user = {
                "user_id": int(user_id), "username": username,
                "registration_date": datetime.now(timezone.utc).isoformat(),
                "profile_completed": False,
                "profile": {"name": None, "email": None, "risk_tolerance": "medium",
                            "investment_goals": None, "preferred_stocks": [], "budget_range": None},
                "watchlist": [], "trading_history": [],
            }
            self.users[key] = user
            self.save_users()
            return user

    def get_user(self, user_id: int) -> Optional[Dict]:
        with self._lock:
            return self.users.get(str(int(user_id)))

    def update_profile(self, user_id: int, profile_data: Dict) -> bool:
        with self._lock:
            user = self.users.get(str(int(user_id)))
            if not user:
                return False
            user.setdefault("profile", {}).update(profile_data)
            user["profile_completed"] = self._is_profile_complete(user["profile"])
            self.save_users()
            return True

    @staticmethod
    def _is_profile_complete(profile: Dict) -> bool:
        return all(profile.get(field) for field in ("name", "email", "risk_tolerance", "investment_goals"))

    def add_to_watchlist(self, user_id: int, stock_symbol: str) -> bool:
        symbol = stock_symbol.strip().upper()
        if not symbol:
            return False
        with self._lock:
            user = self.users.get(str(int(user_id)))
            if not user:
                return False
            watchlist = user.setdefault("watchlist", [])
            if symbol not in watchlist:
                watchlist.append(symbol)
                self.save_users()
            return True

    def remove_from_watchlist(self, user_id: int, stock_symbol: str) -> bool:
        with self._lock:
            user = self.users.get(str(int(user_id)))
            if not user:
                return False
            watchlist = user.setdefault("watchlist", [])
            if stock_symbol in watchlist:
                watchlist.remove(stock_symbol)
                self.save_users()
            return True

    def get_watchlist(self, user_id: int) -> List[str]:
        user = self.get_user(user_id)
        return list(user.get("watchlist", [])) if user else []

    def add_trading_record(self, user_id: int, record: Dict) -> bool:
        with self._lock:
            user = self.users.get(str(int(user_id)))
            if not user:
                return False
            entry = dict(record)
            entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            user.setdefault("trading_history", []).append(entry)
            self.save_users()
            return True

    def get_user_stats(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        if not user:
            return {}
        history = user.get("trading_history", [])
        return {"total_trades": len(history), "watchlist_count": len(user.get("watchlist", [])),
                "profile_completed": bool(user.get("profile_completed")),
                "member_since": user.get("registration_date", "")}
