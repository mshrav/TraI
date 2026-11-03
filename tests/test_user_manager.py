import json
from user_manager import UserManager


def test_user_registration_profile_and_watchlist_are_persisted(tmp_path):
    path = tmp_path / "users.json"
    manager = UserManager(path)
    user = manager.register_user(12345, "sample_user")
    assert user["user_id"] == 12345
    assert manager.add_to_watchlist(12345, "reliance.ns")
    assert manager.get_watchlist(12345) == ["RELIANCE.NS"]
    assert manager.update_profile(12345, {
        "name": "Sample User", "email": "sample@example.test",
        "risk_tolerance": "medium", "investment_goals": "Long term growth",
    })
    assert manager.get_user(12345)["profile_completed"] is True
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert "12345" in on_disk


def test_unknown_user_returns_no_watchlist(tmp_path):
    manager = UserManager(tmp_path / "users.json")
    assert manager.get_watchlist(999) == []
    assert manager.update_profile(999, {"name": "Nobody"}) is False
