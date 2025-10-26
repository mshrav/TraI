import os
import json
import logging
from typing import Dict, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from user_manager import UserManager
from trading_strategy import TradingStrategy, Signal
from data_fetcher import fetch_stock_data
from model_trainer import StockPricePredictor

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ASKING_NAME, ASKING_EMAIL, ASKING_RISK, ASKING_GOALS, ASKING_STOCKS = range(5)

class TelegramTradingBot:
    def __init__(self, token: str):
        self.token = token
        self.user_manager = UserManager()
        self.trading_strategy = TradingStrategy()
        self.predictor = StockPricePredictor()

    def create_app(self):
        """Create and configure the Telegram application."""
        application = Application.builder().token(self.token).build()

        # Add handlers
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_name)],
                ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_email)],
                ASKING_RISK: [CallbackQueryHandler(self.ask_risk)],
                ASKING_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_goals)],
                ASKING_STOCKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_stocks)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("profile", self.show_profile))
        application.add_handler(CommandHandler("analyze", self.analyze_stock))
        application.add_handler(CommandHandler("recommend", self.get_recommendations))
        application.add_handler(CommandHandler("watchlist", self.manage_watchlist))
        application.add_handler(CommandHandler("status", self.bot_status))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        return application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - initiate user registration."""
        user = update.effective_user
        user_id = user.id

        # Register or get existing user
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
        """Handle name input."""
        user_id = update.effective_user.id
        name = update.message.text.strip()

        if len(name) < 2:
            await update.message.reply_text("Please enter a valid name (at least 2 characters):")
            return ASKING_NAME

        context.user_data['name'] = name
        await update.message.reply_text("Great! Now, what's your email address?")
        return ASKING_EMAIL

    async def ask_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle email input."""
        user_id = update.effective_user.id
        email = update.message.text.strip()

        # Basic email validation
        if "@" not in email or "." not in email:
            await update.message.reply_text("Please enter a valid email address:")
            return ASKING_EMAIL

        context.user_data['email'] = email
        await update.message.reply_text(
            "Perfect! Now, what's your risk tolerance level?",
            reply_markup=self.create_risk_keyboard()
        )
        return ASKING_RISK

    def create_risk_keyboard(self):
        """Create inline keyboard for risk level selection."""
        keyboard = [
            [InlineKeyboardButton("🛡️ Low Risk", callback_data="low")],
            [InlineKeyboardButton("⚖️ Medium Risk", callback_data="medium")],
            [InlineKeyboardButton("🎲 High Risk", callback_data="high")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def ask_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle risk level selection."""
        query = update.callback_query
        await query.answer()

        risk_level = query.data
        context.user_data['risk'] = risk_level

        await query.edit_message_text(
            f"Risk level set to: {risk_level.title()}\n\n"
            "What are your investment goals? (e.g., long-term growth, quick profits, stable income)"
        )
        return ASKING_GOALS

    async def ask_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle investment goals input."""
        user_id = update.effective_user.id
        goals = update.message.text.strip()

        if len(goals) < 10:
            await update.message.reply_text("Please provide more details about your investment goals:")
            return ASKING_GOALS

        context.user_data['goals'] = goals

        # Save profile
        profile_data = {
            "name": context.user_data['name'],
            "email": context.user_data['email'],
            "risk_tolerance": context.user_data['risk'],
            "investment_goals": goals
        }

        success = self.user_manager.update_profile(user_id, profile_data)

        if success:
            await update.message.reply_text(
                "🎉 Profile setup complete! You can now use all bot features.\n\n"
                "Use /help to see available commands."
            )
        else:
            await update.message.reply_text("❌ Error saving profile. Please try again.")

        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command."""
        await update.message.reply_text("Profile setup cancelled. Use /start to try again.")
        context.user_data.clear()
        return ConversationHandler.END

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command."""
        user_id = update.effective_user.id
        user = self.user_manager.get_user(user_id)

        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return

        profile = user["profile"]
        stats = self.user_manager.get_user_stats(user_id)

        message = f"👤 *Your Profile*\n\n"
        message += f"Name: {profile.get('name', 'Not set')}\n"
        message += f"Email: {profile.get('email', 'Not set')}\n"
        message += f"Risk Tolerance: {profile.get('risk_tolerance', 'Not set').title()}\n"
        message += f"Investment Goals: {profile.get('investment_goals', 'Not set')}\n\n"
        message += f"📊 *Stats*\n"
        message += f"Watchlist: {stats['watchlist_count']} stocks\n"
        message += f"Total Trades: {stats['total_trades']}\n"
        message += f"Member Since: {stats['member_since'][:10]}\n"

        await update.message.reply_markdown(message)

    async def analyze_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command."""
        user_id = update.effective_user.id
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
            # Fetch data
            data = fetch_stock_data(stock_symbol, "6mo")
            if data.empty:
                await update.message.reply_text(f"❌ Could not fetch data for {stock_symbol}")
                return

            # Train model and predict
            self.predictor.train(data)
            latest = data.tail(1)
            prediction = self.predictor.predict_next_close(latest)

            # Generate trading signals
            signals = self.trading_strategy.generate_signals(data)

            # Format response
            current_price = data['Close'].iloc[-1]
            price_change = prediction - current_price
            change_percent = (price_change / current_price) * 100

            message = f"📈 *{stock_symbol} Analysis*\n\n"
            message += f"Current Price: ₹{current_price:.2f}\n"
            message += f"Predicted Next: ₹{prediction:.2f}\n"
            message += f"Expected Change: {change_percent:+.2f}%\n"

            message += f"\n\n🎯 *Trading Signal*: {signals['signal']}\n"
            message += f"Confidence: {signals['confidence']}%\n"
            message += f"Reason: {signals['reason']}\n\n"

            message += "📊 *Technical Indicators*\n"
            for key, value in signals['indicators'].items():
                message += f"{key.title()}: {value}\n"

            await update.message.reply_markdown(message)

            # Add to watchlist if buy signal
            if signals['signal'] == Signal.BUY.value and signals['confidence'] >= 70:
                self.user_manager.add_to_watchlist(user_id, stock_symbol)
                await update.message.reply_text(f"✅ Added {stock_symbol} to your watchlist!")

        except Exception as e:
            await update.message.reply_text(f"❌ Error analyzing {stock_symbol}: {str(e)}")

    async def get_recommendations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recommend command."""
        user_id = update.effective_user.id
        user = self.user_manager.get_user(user_id)

        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return

        if not user["profile_completed"]:
            await update.message.reply_text("Please complete your profile first using /start.")
            return

        await update.message.reply_text("🔍 Getting personalized recommendations...")

        try:
            # Get user's risk level
            risk_level = user["profile"]["risk_tolerance"]

            # Sample stocks based on risk level
            stock_universe = {
                "low": ["HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS"],
                "medium": ["RELIANCE.NS", "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS"],
                "high": ["BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "AXISBANK.NS"]
            }

            stocks = stock_universe.get(risk_level, stock_universe["medium"])
            recommendations = self.trading_strategy.get_stock_recommendations(stocks, risk_level)

            if not recommendations:
                await update.message.reply_text("❌ No recommendations available at the moment.")
                return

            message = f"🎯 *Personalized Recommendations* (Risk: {risk_level.title()})\n\n"

            for i, rec in enumerate(recommendations[:5], 1):  # Top 5
                message += f"{i}. *{rec['stock']}*\n"
                message += f"   💰 Price: ₹{rec['current_price']:.2f}\n"
                message += f"   🎯 Signal: {rec['signal']}\n"
                message += f"   📊 Confidence: {rec['confidence']}%\n"
                message += f"   💡 {rec['reason']}\n\n"

            await update.message.reply_markdown(message)

        except Exception as e:
            await update.message.reply_text(f"❌ Error getting recommendations: {str(e)}")

    async def manage_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /watchlist command."""
        user_id = update.effective_user.id
        user = self.user_manager.get_user(user_id)

        if not user:
            await update.message.reply_text("Please use /start to register first.")
            return

        watchlist = self.user_manager.get_watchlist(user_id)

        if not watchlist:
            await update.message.reply_text("Your watchlist is empty. Use /analyze to add stocks!")
            return

        message = "📋 *Your Watchlist*\n\n"
        for stock in watchlist:
            message += f"• {stock}\n"

        message += "\nUse /analyze <symbol> to get detailed analysis!"
        await update.message.reply_markdown(message)

    async def bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_count = len(self.user_manager.users)
        await update.message.reply_text(
            f"🤖 *Bot Status*\n\n"
            f"Total Users: {user_count}\n"
            f"Status: Online ✅\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
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
• Higher confidence scores indicate stronger signals

Happy Trading! 📈
        """
        await update.message.reply_markdown(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        text = update.message.text.lower()

        if "hello" in text or "hi" in text:
            await update.message.reply_text("👋 Hello! Use /help to see available commands.")
        elif "thank" in text:
            await update.message.reply_text("😊 You're welcome! Happy trading!")
        else:
            await update.message.reply_text("🤔 I didn't understand that. Use /help to see available commands.")

    def run(self):
        """Run the bot."""
        app = self.create_app()
        print("🤖 AI Trading Bot is running...")
        print("Press Ctrl+C to stop")
        app.run_polling()

if __name__ == "__main__":
    # Load configuration
    with open("bot_config.json", "r") as f:
        config = json.load(f)

    token = config.get("telegram_token")
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ Please set your Telegram bot token in bot_config.json")
        print("Get your token from @BotFather on Telegram")
        exit(1)

    bot = TelegramTradingBot(token)
    bot.run()
