# -*- coding: utf-8 -*-
"""
telegram_notifier.py – Guzo Guest Assist Telegram Notification Center
----------------------------------------------------------------------
Sends alerts and confirmations to the manager group chat via Telegram Bot.
"""

import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

# ✅ Load environment
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")

async def _send_async_message(message: str):
    """Send a Telegram message asynchronously."""
    if not TELEGRAM_BOT_TOKEN or not MANAGER_CHAT_ID:
        print("⚠️ Missing Telegram credentials in .env.")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=MANAGER_CHAT_ID, text=message)
        print(f"📩 Telegram message sent to manager chat: {MANAGER_CHAT_ID}")
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")

def send_telegram_message(message: str):
    """Public synchronous wrapper for easy import."""
    try:
        asyncio.run(_send_async_message(message))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_send_async_message(message))

if __name__ == "__main__":
    send_telegram_message("🚀 Test message from Guzo Guest Assist system – connection OK.")
