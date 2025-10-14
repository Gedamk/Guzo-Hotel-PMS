# -*- coding: utf-8 -*-
"""
get_chat_id.py
----------------------------------------------------
Simple helper script to print your Telegram chat ID.
Run this while your bot is active and send any message
to your bot on Telegram (like "Hi").
----------------------------------------------------
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN missing in .env")
    exit()

print("🔍 Checking for new messages to get chat_id...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()

    if "result" not in data or len(data["result"]) == 0:
        print("⚠️ No recent messages found. Please send a message to your bot first.")
    else:
        for update in data["result"]:
            chat = update.get("message", {}).get("chat", {})
            chat_id = chat.get("id")
            username = chat.get("username", "N/A")
            first_name = chat.get("first_name", "N/A")
            if chat_id:
                print(f"✅ Found chat_id: {chat_id}  |  User: {first_name} (@{username})")
except Exception as e:
    print(f"❌ Error fetching chat_id: {e}")
