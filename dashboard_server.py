"""Local Flask + Socket.IO inbox for Telegram conversations.

The dashboard is intentionally bound to localhost by default. It has no
admin-login layer, so it must not be exposed publicly without authentication,
authorization, HTTPS and deployment hardening.
"""

import json
import os
import asyncio
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from secrets import token_hex
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from settings import ROOT, get_telegram_token

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY') or token_hex(32)
socketio = SocketIO(app, async_mode='threading')

MESSAGES_FILE = ROOT / 'messages.json'
USER_DATA_FILE = ROOT / 'user_data.json'

_bot_token = None


# ---------------------------------------------------------------------------
# Message store
# ---------------------------------------------------------------------------

class MessageStore:
    """Persist and query chat messages shared between the bot and the dashboard."""

    def __init__(self, messages_file=MESSAGES_FILE):
        self.messages_file = Path(messages_file)
        self._lock = threading.RLock()

    # -- low-level I/O -------------------------------------------------------

    def load_messages(self):
        if os.path.exists(self.messages_file):
            try:
                with open(self.messages_file, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                    return payload if isinstance(payload, dict) else {}
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def save_messages(self, messages):
        self.messages_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='messages-', suffix='.tmp', dir=self.messages_file.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.messages_file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    # -- public API ----------------------------------------------------------

    def add_message(self, user_id, sender, text, sent=True):
        """
        Persist one incoming or outgoing message and return its stored dictionary.
        """
        with self._lock:
            messages = self.load_messages()
            uid = str(int(user_id))
            if uid not in messages or not isinstance(messages[uid], list):
                messages[uid] = []

            msg = {
                "sender":           sender,
                "text":             text,
                "timestamp":        datetime.now().isoformat(),
                "sent":             sent,
                "read":             sender == "admin",       # admin msgs auto-read
                "sent_to_telegram": sender != "admin"        # admin msgs still need delivery
            }
            messages[uid].append(msg)
            self.save_messages(messages)
            return msg

    def mark_admin_sent(self, user_id, text):
        """Flag the matching unsent admin message as delivered to Telegram."""
        with self._lock:
            messages = self.load_messages()
            uid = str(user_id)
            if uid in messages:
                for msg in reversed(messages[uid]):
                    if (msg.get("sender") == "admin"
                            and msg.get("text") == text
                            and not msg.get("sent_to_telegram", False)):
                        msg["sent_to_telegram"] = True
                        self.save_messages(messages)
                        return True
        return False

    def get_messages(self, user_id):
        return self.load_messages().get(str(user_id), [])

    def get_all_users(self):
        messages = self.load_messages()
        users = []
        for uid, msgs in messages.items():
            if not isinstance(msgs, list) or not msgs:
                continue
            try:
                numeric_id = int(uid)
            except (TypeError, ValueError):
                continue
            last = msgs[-1] if isinstance(msgs[-1], dict) else {}
            last_text = str(last.get("text", ""))
            info = get_user_info(numeric_id) or {}
            users.append({
                "user_id": numeric_id,
                "name": info.get("name") or f"User {uid}",
                "last_message": last_text[:50] + ("..." if len(last_text) > 50 else ""),
                "last_time": str(last.get("timestamp", "")),
                "unread": sum(1 for m in msgs if isinstance(m, dict) and m.get("sender") == "user" and not m.get("read", False))
            })
        users.sort(key=lambda x: x["last_time"], reverse=True)
        return users

    def mark_read(self, user_id):
        with self._lock:
            messages = self.load_messages()
            uid = str(user_id)
            if uid in messages:
                changed = False
                for msg in messages[uid]:
                    if msg.get("sender") == "user" and not msg.get("read", False):
                        msg["read"] = True
                        changed = True
                if changed:
                    self.save_messages(messages)
            return True


message_store = MessageStore()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_info(user_id):
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(user_id), {}).get("profile", {})
    except Exception:
        return None


def load_bot_token():
    """Load Telegram token from environment first, with local config fallback."""
    global _bot_token
    _bot_token = get_telegram_token()
    if _bot_token:
        print("Telegram token loaded from local configuration")
    else:
        print("Telegram token not configured; outbound replies are disabled")


def send_to_telegram(user_id, text):
    """
    Deliver a message to a Telegram user.

    python-telegram-bot ≥ 20 is fully async.  We spin up a *fresh* event loop
    in the calling thread so we never clash with Flask/SocketIO's event loop.
    """
    global _bot_token
    if not _bot_token:
        load_bot_token()
    if not _bot_token:
        print("❌ No bot token – message not delivered to Telegram")
        return False

    try:
        from telegram import Bot

        async def _send():
            async with Bot(token=_bot_token) as bot:
                await bot.send_message(chat_id=str(user_id), text=text)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        print(f"✅ Delivered to Telegram user {user_id}: {text[:40]}…")
        return True
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
        return False


# Load token at startup
load_bot_token()


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok", "service": "trai-dashboard"})


@app.route('/api/users')
def get_users():
    return jsonify(message_store.get_all_users())


@app.route('/api/users/<int:user_id>/messages')
def get_user_messages(user_id):
    msgs = message_store.get_messages(user_id)
    message_store.mark_read(user_id)          # clear unread badge when chat is opened
    return jsonify(msgs)


@app.route('/api/send', methods=['POST'])
def send_message():
    """Send a dashboard reply and persist it only after Telegram accepts it."""
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get('user_id'))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "A numeric user_id is required"}), 400
    text = str(data.get('text') or '').strip()
    if user_id <= 0 or not text:
        return jsonify({"success": False, "error": "A valid user_id and non-empty text are required"}), 400
    if len(text) > 4096:
        return jsonify({"success": False, "error": "Telegram messages must be 4096 characters or fewer"}), 400
    if not _bot_token:
        return jsonify({"success": False, "error": "Telegram bot token is not configured"}), 503
    if not send_to_telegram(user_id, text):
        return jsonify({"success": False, "error": "Telegram delivery failed; check bot token, chat ID and bot logs"}), 502

    msg = message_store.add_message(user_id, "admin", text, sent=True)
    # Persist delivery state after the successful Telegram API call.
    message_store.mark_admin_sent(user_id, text)
    msg["sent_to_telegram"] = True
    socketio.emit('new_message', {"user_id": user_id, "message": msg})
    socketio.emit('user_updated', message_store.get_all_users())
    return jsonify({"success": True, "message": msg, "delivery_status": "sent"})


@app.route('/api/users/<int:user_id>/mark_read', methods=['POST'])
def mark_read(user_id):
    message_store.mark_read(user_id)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Telegram → Dashboard entry-point
# ---------------------------------------------------------------------------

def on_telegram_message(user_id, text, username=None):
    """
    Called from the webhook route (and can be imported by the bot process).
    Persists the user message and pushes it to all dashboard browsers in real time.
    """
    msg = message_store.add_message(user_id, "user", text, sent=True)

    socketio.emit('new_message', {"user_id": user_id, "message": msg})
    socketio.emit('user_updated', message_store.get_all_users())


@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    The bot process POSTs every incoming Telegram update here so the dashboard
    is notified in real time without the two processes sharing memory.
    """
    expected = os.getenv('DASHBOARD_WEBHOOK_TOKEN', '').strip()
    supplied = request.headers.get('X-TraI-Webhook-Token', '').strip()
    if expected and supplied != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    update = request.get_json(silent=True) or {}
    message = update.get('message')
    if isinstance(message, dict) and message.get('text') and isinstance(message.get('chat'), dict):
        user_id = message['chat'].get('id')
        if user_id is not None:
            on_telegram_message(user_id, str(message['text']), message['chat'].get('username', ''))
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    print('Dashboard browser connected')
    emit('connected', {'data': 'Connected to dashboard'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Dashboard browser disconnected')


@socketio.on('request_users')
def handle_request_users():
    emit('users_list', message_store.get_all_users())


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def run_server():
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    print(f"TraI dashboard starting at http://{host}:{port}")
    if host not in ("127.0.0.1", "localhost"):
        print("WARNING: dashboard has no user login; do not expose it to the public internet.")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server()
