# -*- coding: utf-8 -*-
"""
telegram_notifier.py – Guzo Guest Assist Telegram Notification Utility
----------------------------------------------------------------------
Sends status updates or report summaries to Telegram chats
(using the bot token defined in .env).
"""

import os
import requests
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # fallback chat ID if not provided


# ------------------------------------------------------------
# Core Send Function
# ------------------------------------------------------------
def send_telegram_message(message: str, chat_id: str = None) -> bool:
    """
    Send a plain text message to a Telegram chat.

    :param message: The message text to send.
    :param chat_id: Telegram chat ID (string or int). Defaults to ADMIN_CHAT_ID if not provided.
    :return: True if successful, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[TelegramNotifier] ⚠️ No TELEGRAM_BOT_TOKEN found in .env file.")
        return False

    chat_id = chat_id or DEFAULT_CHAT_ID
    if not chat_id:
        print("[TelegramNotifier] ⚠️ No chat_id specified or ADMIN_CHAT_ID not set.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[TelegramNotifier] ✅ Message sent successfully to chat_id {chat_id}")
            return True
        else:
            print(f"[TelegramNotifier] ❌ Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"[TelegramNotifier] 💥 Exception while sending Telegram message: {e}")
    return False
if __name__ == "__main__":
    print("🔍 Testing Telegram Notifier...")
    success = send_telegram_message("✅ Guzo Telegram Notifier test successful!")
    if success:
        print("📨 Test message sent successfully.")
    else:
        print("⚠️ Failed to send test message. Check TELEGRAM_BOT_TOKEN or ADMIN_CHAT_ID.")
