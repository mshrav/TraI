import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class UserManager:
    def __init__(self, data_file: str = "user_data.json"):
        self.data_file = data_file
        self.users = self.load_users()

    def load_users(self) -> Dict:
        """Load user data from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Corrupted user data file. Starting fresh.")
                return {}
        return {}

    def save_users(self):
        """Save user data to JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    def register_user(self, user_id: int, username: str = None) -> Dict:
        """Register a new user."""
        if str(user_id) in self.users:
            return self.users[str(user_id)]

        user_data = {
            "user_id": user_id,
            "username": username,
            "registration_date": datetime.now().isoformat(),
            "profile_completed": False,
            "profile": {
                "name": None,
                "email": None,
                "risk_tolerance": "medium",
                "investment_goals": None,
                "preferred_stocks": [],
                "budget_range": None
            },
            "watchlist": [],
            "trading_history": []
        }

        self.users[str(user_id)] = user_data
        self.save_users()
        return user_data

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data by user ID."""
        return self.users.get(str(user_id))

    def update_profile(self, user_id: int, profile_data: Dict) -> bool:
        """Update user profile."""
        if str(user_id) not in self.users:
            return False

        self.users[str(user_id)]["profile"].update(profile_data)
        self.users[str(user_id)]["profile_completed"] = self._is_profile_complete(
            self.users[str(user_id)]["profile"]
        )
        self.save_users()
        return True

    def _is_profile_complete(self, profile: Dict) -> bool:
        """Check if user profile is complete."""
        required_fields = ["name", "email", "risk_tolerance", "investment_goals"]
        return all(profile.get(field) for field in required_fields)

    def add_to_watchlist(self, user_id: int, stock_symbol: str) -> bool:
        """Add stock to user's watchlist."""
        if str(user_id) not in self.users:
            return False

        watchlist = self.users[str(user_id)]["watchlist"]
        if stock_symbol not in watchlist:
            watchlist.append(stock_symbol)
            self.save_users()
        return True

    def remove_from_watchlist(self, user_id: int, stock_symbol: str) -> bool:
        """Remove stock from user's watchlist."""
        if str(user_id) not in self.users:
            return False

        watchlist = self.users[str(user_id)]["watchlist"]
        if stock_symbol in watchlist:
            watchlist.remove(stock_symbol)
            self.save_users()
        return True

    def get_watchlist(self, user_id: int) -> List[str]:
        """Get user's watchlist."""
        user = self.get_user(user_id)
        return user["watchlist"] if user else []

    def add_trading_record(self, user_id: int, record: Dict) -> bool:
        """Add a trading record for the user."""
        if str(user_id) not in self.users:
            return False

        record["timestamp"] = datetime.now().isoformat()
        self.users[str(user_id)]["trading_history"].append(record)
        self.save_users()
        return True

    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics."""
        user = self.get_user(user_id)
        if not user:
            return {}

        history = user["trading_history"]
        return {
            "total_trades": len(history),
            "watchlist_count": len(user["watchlist"]),
            "profile_completed": user["profile_completed"],
            "member_since": user["registration_date"]
        }
