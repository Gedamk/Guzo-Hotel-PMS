# -*- coding: utf-8 -*-
"""
bot_main.py – Guzo Guest Assist (v6.0 English-Only Clean Edition)
-----------------------------------------------------------------
Main Telegram bot entry point for Guzo Guest Assist.
Handles conversational booking and ensures UTF-8 output (emojis show correctly).
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# --- Force UTF-8 everywhere (fixes emoji/output issues) ---
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# --- Load environment variables ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN is missing in your .env file.")
    sys.exit(1)

# --- Import project modules ---
from guzo_booking_bot.modules.conversational_booking import create_booking_conversation_handler
from guzo_booking_bot.modules.log_helper import log_event

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "Guest"
    welcome_msg = (
        f"👋 Hello {user}! Welcome to *Guzo Guest Assist*.\n\n"
        "I can help you make a hotel reservation.\n"
        "Simply type *book room* or use the /book command to start.\n\n"
        "You can cancel anytime by typing /cancel."
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")
    log_event("System", "START", f"{user} started interaction.")

# --- Help Command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🆘 *Help – Guzo Guest Assist*\n\n"
        "• /start – Begin using the assistant\n"
        "• /book – Start a new hotel booking\n"
        "• /cancel – Cancel current booking process\n"
        "• Type *book room* anytime to begin."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- Main function ---
def main():
    print("🚀 Starting Guzo Guest Assist Bot...")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("===============================================")
    print("UTF-8 encoding active ✅")
    print("Bot is connecting to Telegram...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add conversation handler from your module
    booking_handler = create_booking_conversation_handler()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(booking_handler)

    print("🤖 Bot is now running 24/7... Press Ctrl + C to stop.")
    log_event("System", "RUNNING", "Bot started successfully.")
    app.run_polling()

# --- Run the bot ---
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped manually.")
    except Exception as e:
        print(f"⚠️ Bot crashed: {e}")
        log_event("System", "ERROR", str(e))
