# -*- coding: utf-8 -*-
"""
env_loader.py – Central environment loader for Guzo Guest Assist.
Ensures .env variables (SendGrid, Telegram, Twilio, etc.) are loaded globally.
"""

import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

def init_env():
    """Ensure .env is loaded across all modules."""
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH, override=True)
        print(f"✅ Environment loaded from: {ENV_PATH}")
        key = os.getenv("SENDGRID_API_KEY")
        print("SENDGRID_API_KEY configured:", bool(key))
    else:
        print(f"⚠️ .env file not found at {ENV_PATH}")
