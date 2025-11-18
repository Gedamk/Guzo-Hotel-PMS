# -*- coding: utf-8 -*-
"""
test_bot.py — Telegram Bot Connection Test (Safe Version)
---------------------------------------------------------
✅ Loads token securely from .env
✅ Validates token before starting
✅ Handles invalid token or network errors gracefully
"""

import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv


# =====================================================
# 1. Load Environment
# =====================================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env file.")
    exit(1)


# =====================================================
# 2. Validate Token Before Starting
# =====================================================
def validate_token(token: str) -> bool:
    """Check if Telegram bot token is valid."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("ok"):
            print(f"✅ Token is valid. Logged in as: {data['result']['first_name']} (@{data['result']['username']})")
            return True
        else:
            print(f"❌ Invalid token or unauthorized: {data.get('description')}")
            return False
    except Exception as e:
        print(f"⚠️ Network or API error: {e}")
        return False


if not validate_token(TOKEN):
    print("🛑 Bot startup aborted — please check your token in BotFather.")
    exit(1)


# =====================================================
# 3. Define Handlers
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! The bot is now connected and running safely!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")


# =====================================================
# 4. Start Bot
# =====================================================
def main():
    print("🚀 Launching Telegram bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("✅ Bot is now polling for messages. Press CTRL + C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
