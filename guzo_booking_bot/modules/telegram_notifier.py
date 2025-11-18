# -*- coding: utf-8 -*-
"""
telegram_notifier.py – Guzo Guest Assist Admin Alerts (v1.0)
------------------------------------------------------------
Sends Telegram notifications to the Guzo Admin Chat for
system events, missing sheets, or guest sentiment alerts.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "-4989050231")  # default Guzo admin chat

def notify_admin(message: str):
    """Send alert message to admin chat via Telegram."""
    if not TOKEN:
        print("[Notifier] ❌ Missing TELEGRAM_BOT_TOKEN in .env")
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"[Notifier] ✅ Sent admin alert: {message[:60]}...")
        else:
            print(f"[Notifier] ⚠️ Telegram API error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[Notifier] ⚠️ Failed to send admin alert: {e}")
