# -*- coding: utf-8 -*-
"""
Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram Notification Module
-------------------------------------------------
Sends a concise Telegram message to the manager channel after
each automation task (report generation, email delivery, etc.).

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Simple, secure, and reliable.
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Follows the "invisible power" philosophy.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")  # e.g. 123456789

def send_telegram_message(text: str):
    """Send a Telegram message with graceful failure handling."""
    if not TELEGRAM_TOKEN or not MANAGER_CHAT_ID:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Telegram not configured. Skipping notification.")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": MANAGER_CHAT_ID, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Telegram notification sent successfully.")
            return True
        else:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Telegram API error: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram send failed: {e}")
        return False


# Optional: Standalone test
if __name__ == "__main__":
    send_telegram_message("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Test message from Guzo Guest Assist automation.")
