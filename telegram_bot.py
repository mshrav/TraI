"""TraI Telegram bot: profile management, stock analysis and watchlists.

This bot is analysis-only. It does not place real orders. Incoming text is sent
once to the local dashboard webhook; when the dashboard is offline, the bot
uses a local JSON fallback. Dashboard replies are delivered only by the
Dashboard HTTP handler, avoiding competing send loops.
"""

import os
import asyncio
import json
import logging
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from user_manager import UserManager
from settings import data_path, get_telegram_token
from trading_strategy import TradingStrategy, Signal
from data_fetcher import fetch_stock_data
from model_trainer import StockPricePredictor
import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / shared state
# ---------------------------------------------------------------------------

ASKING_NAME, ASKING_EMAIL, ASKING_RISK, ASKING_GOALS = range(4)

MESSAGES_FILE = str(data_path("messages.json"))
DASHBOARD_URL = os.getenv("DASHBOARD_WEBHOOK_URL", "http://127.0.0.1:5000/webhook/telegram")
_messages_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Dashboard helper
# ---------------------------------------------------------------------------

def save_message_to_dashboard(user_id: int, sender: str, text: str):
    """Send a Telegram message to the local dashboard; use JSON fallback offline.

    The dashboard is the single writer while online. This avoids the old double
    persistence path where both processes appended the same incoming message.
    """
    headers = {}
    webhook_token = os.getenv("DASHBOARD_WEBHOOK_TOKEN", "").strip()
    if webhook_token:
        headers["X-TraI-Webhook-Token"] = webhook_token
    try:
        response = requests.post(
            DASHBOARD_URL,
            json={"message": {"chat": {"id": int(user_id)}, "text": str(text)}},
            headers=headers,
            timeout=3,
        )
        response.raise_for_status()
        return
    except requests.RequestException as exc:
        logger.debug("Dashboard webhook unavailable; storing message locally: %s", exc)

    # Offline fallback. Atomic file replacement reduces the chance of a partial JSON file.
    try:
        with _messages_lock:
            messages = {}
            if os.path.exists(MESSAGES_FILE):
                try:
                    with open(MESSAGES_FILE, "r", encoding="utf-8") as handle:
                        loaded = json.load(handle)
                        messages = loaded if isinstance(loaded, dict) else {}
                except (json.JSONDecodeError, OSError):
                    messages = {}
            uid = str(int(user_id))
            messages.setdefault(uid, []).append({
                "sender": sender, "text": str(text), "timestamp": datetime.now().astimezone().isoformat(),
                "sent": True, "read": sender == "admin", "sent_to_telegram": sender != "admin",
            })
            temporary = MESSAGES_FILE + ".tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(messages, handle, indent=2, ensure_ascii=False)
            os.replace(temporary, MESSAGES_FILE)
    except Exception:
        logger.exception("Unable to save message to dashboard fallback store")


# ---------------------------------------------------------------------------
# Bot class
# ---------------------------------------------------------------------------

class TelegramTradingBot:
    def __init__(self, token: str):
        self.token            = token
        self.user_manager     = UserManager()
        self.trading_strategy = TradingStrategy()
        self.predictor        = StockPricePredictor()

    # -- Application factory -------------------------------------------------

    def create_app(self):
        application = Application.builder().token(self.token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                ASKING_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_name)],
                ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_email)],
                ASKING_RISK:  [CallbackQueryHandler(self.ask_risk)],
                ASKING_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_goals)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("profile",   self.show_profile))
        application.add_handler(CommandHandler("analyze",   self.analyze_stock))
        application.add_handler(CommandHandler("recommend", self.get_recommendations))
        application.add_handler(CommandHandler("watchlist", self.manage_watchlist))
        application.add_handler(CommandHandler("status",    self.bot_status))
        application.add_handler(CommandHandler("help",      self.help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        return application

    # -- Shared helper -------------------------------------------------------

    def _notify_dashboard(self, user_id: int, text: str):
        """Notify the dashboard without blocking Telegram's async event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(save_message_to_dashboard, user_id, "user", text))
        except RuntimeError:
            save_message_to_dashboard(user_id, "user", text)

    # -- Handlers ------------------------------------------------------------

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user    = update.effective_user
        user_id = user.id

        # FIX: notify dashboard for /start as well
        self._notify_dashboard(user_id, "/start")

        user_data = self.user_manager.register_user(user_id, user.username)

        if user_data["profile_completed"]:
            await update.message.reply_text(
                f"🤖 Welcome back to AI Trading Bot, {user_data['profile']['name']}!\n\n"
                "Use /help to see available commands."
            )
        else:
            await update.message.reply_text(
                "🤖 Welcome to AI Trading Bot!\n\n"
                "I need some information to provide personalized trading recommendations. "
                "Let's set up your profile.\n\n"
                "What's your full name?"
            )
            return ASKING_NAME

    async def ask_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        name    = update.message.text.strip()
        self._notify_dashboard(user_id, name)

        if len(name) < 2:
            await update.message.reply_text("Please enter a valid name (at least 2 characters):")
            return ASKING_NAME

        context.user_data['name'] = name
        await update.message.reply_text("Great! Now, what's your email address?")
        return ASKING_EMAIL

    async def ask_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        email   = update.message.text.strip()
        self._notify_dashboard(user_id, email)

        if "@" not in email or "." not in email:
            await update.message.reply_text("Please enter a valid email address:")
            return ASKING_EMAIL

        context.user_data['email'] = email
        await update.message.reply_text(
            "Perfect! Now, what's your risk tolerance level?",
            reply_markup=self._risk_keyboard(),
        )
        return ASKING_RISK

    def _risk_keyboard(self):
        keyboard = [
            [InlineKeyboardButton("🛡️ Low Risk",    callback_data="low")],
            [InlineKeyboardButton("⚖️ Medium Risk", callback_data="medium")],
            [InlineKeyboardButton("🎲 High Risk",   callback_data="high")],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def ask_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query      = update.callback_query
        await query.answer()
        risk_level = query.data
        context.user_data['risk'] = risk_level
        self._notify_dashboard(query.from_user.id, f"[risk selected: {risk_level}]")

        await query.edit_message_text(
            f"Risk level set to: {risk_level.title()}\n\n"
            "What are your investment goals? (e.g., long-term growth, quick profits, stable income)"
        )
        return ASKING_GOALS

    async def ask_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        goals   = update.message.text.strip()
        self._notify_dashboard(user_id, goals)

        if len(goals) < 10:
            await update.message.reply_text("Please provide more details about your investment goals:")
            return ASKING_GOALS

        context.user_data['goals'] = goals
        profile_data = {
            "name":             context.user_data['name'],
            "email":            context.user_data['email'],
            "risk_tolerance":   context.user_data['risk'],
            "investment_goals": goals,
        }
        success = self.user_manager.update_profile(user_id, profile_data)

        if success:
            await update.message.reply_text(
                "🎉 Profile setup complete! You can now use all bot features.\n\n"
                "Use /help to see available commands."
            )
        else:
            await update.message.reply_text("❌ Error saving profile. Please try again.")

        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._notify_dashboard(update.effective_user.id, "/cancel")
        await update.message.reply_text("Profile setup cancelled. Use /start to try again.")
        context.user_data.clear()
        return ConversationHandler.END

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._notify_dashboard(user_id, "/profile")

        user = self.user_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return

        profile = user["profile"]
        stats   = self.user_manager.get_user_stats(user_id)

        msg  = "👤 *Your Profile*\n\n"
        msg += f"Name: {profile.get('name', 'Not set')}\n"
        msg += f"Email: {profile.get('email', 'Not set')}\n"
        msg += f"Risk Tolerance: {profile.get('risk_tolerance', 'Not set').title()}\n"
        msg += f"Investment Goals: {profile.get('investment_goals', 'Not set')}\n\n"
        msg += "📊 *Stats*\n"
        msg += f"Watchlist: {stats['watchlist_count']} stocks\n"
        msg += f"Total Trades: {stats['total_trades']}\n"
        msg += f"Member Since: {stats['member_since'][:10]}\n"

        await update.message.reply_markdown(msg)

    async def analyze_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        cmd_text = "/analyze " + " ".join(context.args) if context.args else "/analyze"
        self._notify_dashboard(user_id, cmd_text)

        user = self.user_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return
        if not user["profile_completed"]:
            await update.message.reply_text("Please complete your profile first using /start.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /analyze <STOCK_SYMBOL>\nExample: /analyze RELIANCE.NS")
            return

        stock_symbol = context.args[0].upper()
        await update.message.reply_text(f"🔍 Analyzing {stock_symbol}...")

        try:
            data = fetch_stock_data(stock_symbol, "6mo")
            if data.empty:
                await update.message.reply_text(f"❌ Could not fetch data for {stock_symbol}")
                return

            model_metrics = self.predictor.train(data)
            latest     = data.tail(1)
            prediction = self.predictor.predict_next_close(latest)
            signals    = self.trading_strategy.generate_signals(data)

            current_price  = data['Close'].iloc[-1]
            price_change   = prediction - current_price
            change_percent = (price_change / current_price) * 100

            msg  = f"📈 *{stock_symbol} Analysis*\n\n"
            msg += f"Current Price: ₹{current_price:.2f}\n"
            msg += f"Predicted Next: ₹{prediction:.2f}\n"
            msg += f"Expected Change: {change_percent:+.2f}%\n"
            msg += f"\n🧪 *Chronological Holdout Evaluation*\n"
            msg += f"MAE: ₹{model_metrics['mae']:.2f} | RMSE: ₹{model_metrics['rmse']:.2f}\n"
            msg += f"Directional accuracy: {model_metrics['directional_accuracy_pct']:.1f}%\n"
            msg += f"\n🎯 *Technical Signal*: {signals['signal']}\n"
            msg += f"Rule score: {signals['confidence']}/100\n"
            msg += f"Reason: {signals['reason']}\n\n"
            msg += "📊 *Technical Indicators*\n"
            for key, value in signals['indicators'].items():
                msg += f"{key.title()}: {value}\n"

            await update.message.reply_markdown(msg)

            if signals['signal'] == Signal.BUY.value and signals['confidence'] >= 70:
                self.user_manager.add_to_watchlist(user_id, stock_symbol)
                await update.message.reply_text(f"✅ Added {stock_symbol} to your watchlist!")

        except Exception as e:
            await update.message.reply_text(f"❌ Error analyzing {stock_symbol}: {e}")

    async def get_recommendations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._notify_dashboard(user_id, "/recommend")

        user = self.user_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return
        if not user["profile_completed"]:
            await update.message.reply_text("Please complete your profile first using /start.")
            return

        await update.message.reply_text("🔍 Getting personalized recommendations...")

        try:
            risk_level     = user["profile"]["risk_tolerance"]
            stock_universe = {
                "low":    ["HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS"],
                "medium": ["RELIANCE.NS", "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS"],
                "high":   ["BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "AXISBANK.NS"],
            }
            stocks          = stock_universe.get(risk_level, stock_universe["medium"])
            recommendations = self.trading_strategy.get_stock_recommendations(stocks, risk_level)

            if not recommendations:
                await update.message.reply_text("❌ No recommendations available at the moment.")
                return

            msg = f"🎯 *Personalized Recommendations* (Risk: {risk_level.title()})\n\n"
            for i, rec in enumerate(recommendations[:5], 1):
                msg += f"{i}. *{rec['stock']}*\n"
                msg += f"   💰 Price: ₹{rec['current_price']:.2f}\n"
                msg += f"   🎯 Signal: {rec['signal']}\n"
                msg += f"   📊 Rule score: {rec['confidence']}/100\n"
                msg += f"   💡 {rec['reason']}\n\n"

            await update.message.reply_markdown(msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Error getting recommendations: {e}")

    async def manage_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._notify_dashboard(user_id, "/watchlist")

        user = self.user_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return

        watchlist = self.user_manager.get_watchlist(user_id)
        if not watchlist:
            await update.message.reply_text("Your watchlist is empty. Use /analyze to add stocks!")
            return

        msg = "📋 *Your Watchlist*\n\n"
        for stock in watchlist:
            msg += f"• {stock}\n"
        msg += "\nUse /analyze <symbol> to get detailed analysis!"
        await update.message.reply_markdown(msg)

    async def bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._notify_dashboard(user_id, "/status")

        user_count = len(self.user_manager.users)
        await update.message.reply_text(
            f"🤖 *Bot Status*\n\n"
            f"Total Users: {user_count}\n"
            f"Status: Online ✅\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._notify_dashboard(user_id, "/help")

        help_text = """
🤖 *AI Trading Bot Commands*

📝 *Setup*
/start - Register and set up your profile
/profile - View your profile and stats

📊 *Trading*
/analyze <symbol> - Analyze a specific stock
/recommend - Get personalized stock recommendations
/watchlist - View your stock watchlist

ℹ️ *Info*
/status - Check bot status
/help - Show this help message

💡 *Tips*
• Use stock symbols like RELIANCE.NS for Indian stocks
• Complete your profile for better recommendations
• Signal scores measure rule strength, not a probability of profit

Happy Trading! 📈
        """
        await update.message.reply_markdown(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle free-text messages and save them to the dashboard."""
        user_id = update.effective_user.id
        text    = update.message.text

        # FIX: save via helper (not inline requests.post) so fields are consistent
        self._notify_dashboard(user_id, text)

        text_lower = text.lower()
        if "hello" in text_lower or "hi" in text_lower:
            await update.message.reply_text("👋 Hello! Use /help to see available commands.")
        elif "thank" in text_lower:
            await update.message.reply_text("😊 You're welcome! Happy trading!")
        else:
            await update.message.reply_text("🤔 I didn't understand that. Use /help to see available commands.")

    # -- Runner --------------------------------------------------------------

    def run(self):
        application = self.create_app()

        print("🤖 AI Trading Bot is running… (press Ctrl+C to stop)")
        application.run_polling()


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    token = get_telegram_token()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your .env file before starting the Telegram bot.")
    TelegramTradingBot(token).run()
