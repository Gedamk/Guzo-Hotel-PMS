# -*- coding: utf-8 -*-
"""
weekly_report.py – Guzo Guest Assist
------------------------------------
Generates and emails weekly reports to hotel managers.
"""

# 🚨 Load .env before any module imports
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
dotenv_path = os.path.join(BASE_DIR, ".env")

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
    print(f"✅ Environment loaded successfully from: {dotenv_path}")
else:
    print(f"⚠️ .env file not found at: {dotenv_path}")

print("🔍 SENDGRID_API_KEY prefix:", (os.getenv("SENDGRID_API_KEY") or "❌ Missing")[:10])

# Only after this line should your other imports come in:
from guzo_booking_bot.modules.email_sender import send_invoice_email
from guzo_booking_bot.modules.google_sheets import init_client, load_hotel_contacts
# ... (rest of your imports)
