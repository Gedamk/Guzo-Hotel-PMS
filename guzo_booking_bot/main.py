# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Multi-Channel Bot
-------------------------------------
Main Telegram entry point for Guzo Guest Assist.
Handles guest and hotel messages, registration, and routing.
"""

import sys
import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# ✅ Add parent directory to path (so imports work)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# ✅ Internal imports
from guzo_booking_bot.message_router import process_message
from guzo_booking_bot.modules.register_hotel import register_hotel  # 🔹 new import

# ✅ Load environment variables
load_dotenv()
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not telegram_token:
    print("❌ TELEGRAM_BOT_TOKEN missing in .env file.")
    sys.exit(1)

# ✅ UTF-8 Fix
sys.stdout.reconfigure(encoding="utf-8")

# ======================================================
# LOGGING
# ======================================================
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    format="%(asctime)s - GuzoBot - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "logs", "bot.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GuzoBot")

# ======================================================
# TELEGRAM HANDLERS
# ======================================================

async def start(update, context):
    """Welcome message."""
    await update.message.reply_text("👋 Welcome to Guzo Guest Assist! How can we help you today?")
    logger.info(f"Started chat with {update.effective_user.username or update.effective_user.id}")

async def handle_text(update, context):
    """Handle guest/hotel messages."""
    user = update.effective_user
    text = update.message.text
    logger.info(f"Message from {user.username or user.id}: {text}")
    reply = process_message("telegram", user.id, text)
    await update.message.reply_text(reply)

# ======================================================
# MAIN FUNCTION
# ======================================================
def main():
    try:
        logger.info("🚀 Launching Telegram Bot...")
        app = ApplicationBuilder().token(telegram_token).build()

        # 🔹 Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("register", register_hotel))  # ✅ new /register handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        print("🤖 Guzo Guest Assist Telegram bot is running...")
        app.run_polling()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
