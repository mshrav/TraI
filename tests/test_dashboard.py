"""Dashboard integration tests run when Flask/Flask-SocketIO are installed."""
import pytest
pytest.importorskip("flask")
pytest.importorskip("flask_socketio")
import dashboard_server as dashboard


def test_health_endpoint():
    response = dashboard.app.test_client().get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_message_store_persists_and_marks_read(tmp_path):
    store = dashboard.MessageStore(tmp_path / "messages.json")
    store.add_message(123, "user", "hello")
    assert store.get_messages(123)[0]["text"] == "hello"
    store.mark_read(123)
    assert store.get_messages(123)[0]["read"] is True


def test_send_rejects_invalid_payload():
    response = dashboard.app.test_client().post("/api/send", json={"user_id": "bad", "text": "hello"})
    assert response.status_code == 400


def test_send_persists_only_after_successful_delivery(tmp_path, monkeypatch):
    store = dashboard.MessageStore(tmp_path / "messages.json")
    monkeypatch.setattr(dashboard, "message_store", store)
    monkeypatch.setattr(dashboard, "_bot_token", "test-token")
    monkeypatch.setattr(dashboard, "send_to_telegram", lambda user_id, text: True)
    response = dashboard.app.test_client().post("/api/send", json={"user_id": 123, "text": "hello"})
    assert response.status_code == 200
    assert response.get_json()["delivery_status"] == "sent"
    assert store.get_messages(123)[0]["sent_to_telegram"] is True


def test_send_does_not_persist_when_delivery_fails(tmp_path, monkeypatch):
    store = dashboard.MessageStore(tmp_path / "messages.json")
    monkeypatch.setattr(dashboard, "message_store", store)
    monkeypatch.setattr(dashboard, "_bot_token", "test-token")
    monkeypatch.setattr(dashboard, "send_to_telegram", lambda user_id, text: False)
    response = dashboard.app.test_client().post("/api/send", json={"user_id": 123, "text": "hello"})
    assert response.status_code == 502
    assert store.get_messages(123) == []
