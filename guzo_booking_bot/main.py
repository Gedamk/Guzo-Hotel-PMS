# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Multi-Channel Bot
Main Telegram entrypoint
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from guzo_booking_bot.message_router import process_message
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure logging for console + file output
logging.basicConfig(
    format="%(asctime)s - GuzoBot - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- Telegram Bot Handlers ---

async def start(update, context):
    """Welcome message when user starts the bot."""
    await update.message.reply_text("Welcome to Guzo Guest Assist! How can we help you today?")

async def handle_text(update, context):
    """Handle any guest message and send reply."""
    user = update.effective_user
    message_text = update.message.text
    reply_text = process_message("telegram", user.id, message_text)
    await update.message.reply_text(reply_text)

def main():
    """Run Telegram bot."""
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        print("❌ TELEGRAM_TOKEN missing in .env file.")
        return

    app = ApplicationBuilder().token(telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Guzo Guest Assist Telegram bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
