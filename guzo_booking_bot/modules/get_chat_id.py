# -*- coding: utf-8 -*-
"""
get_chat_id.py — Final stable version for Telegram v21.5 and Python 3.12 (Windows safe)
Retrieves and prints your Telegram Chat ID.
"""

import os
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment
ENV_PATH = r"C:\Users\Gedan\Desktop\Guzo\.env"
load_dotenv(dotenv_path=ENV_PATH)
TOKEN = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()

print(f"Token configured: {bool(TOKEN)} (len={len(TOKEN)})")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"✅ Your chat ID is: {chat_id}")
    print(f"📩 Chat ID received: {chat_id}")

async def run_bot():
    """Runs bot safely inside an async loop."""
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN missing.")
        return

    # Validate token
    try:
        bot = Bot(TOKEN)
        me = await bot.get_me()
        print(f"✅ Token verified — @{me.username}")
    except Exception as e:
        print(f"❌ Token test failed: {e}")
        return

    # Build the application safely
    print("🤖 Creating Application safely...")
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("start", start))

    print("✅ Bot is running. Send /start to your bot in Telegram.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # Keep running until interrupted
    await asyncio.Event().wait()

def main():
    """Ensures the bot runs even if loop is already active."""
    try:
        asyncio.run(run_bot())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(run_bot())
        loop.run_forever()

if __name__ == "__main__":
    main()
