# -*- coding: utf-8 -*-
"""
check_token.py — Telegram Bot Token Validator
----------------------------------------------
Verifies your TELEGRAM_BOT_TOKEN from .env before launching the bot.
"""

import os
import requests
from dotenv import load_dotenv

# Load token from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    print("❌ No TELEGRAM_BOT_TOKEN found in .env file.")
    exit(1)

# Call Telegram API to test the token
url = f"https://api.telegram.org/bot{token}/getMe"
try:
    response = requests.get(url, timeout=10)
    data = response.json()
except Exception as e:
    print(f"⚠️ Connection error: {e}")
    exit(1)

if data.get("ok"):
    bot_name = data["result"]["first_name"]
    bot_username = data["result"]["username"]
    print(f"✅ Token is VALID for bot: {bot_name} (@{bot_username})")
else:
    print(f"❌ INVALID token — Telegram says: {data.get('description')}")
