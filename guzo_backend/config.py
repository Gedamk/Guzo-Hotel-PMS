# -*- coding: utf-8 -*-
"""
🌍 Guzo Guest Assist — Configuration (v3)
-------------------------------------------------
Central configuration file for environment management,
API keys, and integrations (Telegram, Email, Google Sheets, Twilio, etc.)

✅ Simple, secure, and scalable.
✅ Works seamlessly with .env and project structure.
"""

import os
from dotenv import load_dotenv

# ----------------------------------------
# Base Paths & Environment Setup
# ----------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Load environment variables from .env file
load_dotenv(dotenv_path=ENV_PATH, override=True)

# ----------------------------------------
# Telegram Configuration
# ----------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ----------------------------------------
# Email Configuration
# ----------------------------------------
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "sendgrid").strip().lower()

# --- SendGrid ---
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_SENDER_EMAIL = os.getenv("SENDGRID_SENDER_EMAIL", "")
SENDGRID_SENDER_NAME = os.getenv("SENDGRID_SENDER_NAME", "Guzo Guest Assist")

# --- Gmail (App Password required) ---
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")

# ----------------------------------------
# Google Sheets / Drive
# ----------------------------------------
SERVICE_ACCOUNT_FILE = os.getenv(
    "SERVICE_ACCOUNT_FILE",
    os.path.join(BASE_DIR, "guzo_backend", "creds", "guzo_service_account.json")
)

GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", SERVICE_ACCOUNT_FILE)
GOOGLE_CREDS_FILE = GOOGLE_CREDS  # backward compatibility

SPREADSHEET_GUEST_ASSIST_ID = os.getenv("SPREADSHEET_GUEST_ASSIST_ID", "")
SPREADSHEET_HOTEL_CONTACTS_ID = os.getenv("SPREADSHEET_HOTEL_CONTACTS_ID", "")
SPREADSHEET_NOTIFICATIONSLOG_ID = os.getenv("SPREADSHEET_NOTIFICATIONSLOG_ID", "")

GOOGLE_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

# ----------------------------------------
# Twilio (SMS / WhatsApp)
# ----------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ----------------------------------------
# Environment
# ----------------------------------------
ENV = os.getenv("ENV", "development").lower()

# ----------------------------------------
# Debug Helper
# ----------------------------------------
def _debug_dump():
    """Print a safe configuration summary."""
    print("\n🧩 Guzo Config Debug Summary")
    print("-----------------------------")
    print("ENV_PATH:", ENV_PATH)
    print("TELEGRAM_TOKEN:", "✅ Loaded" if TELEGRAM_TOKEN else "❌ Missing")
    print("EMAIL_PROVIDER:", EMAIL_PROVIDER)
    print("SENDGRID Key:", "✅ Present" if SENDGRID_API_KEY else "❌ Missing")
    print("GMAIL Email:", GMAIL_EMAIL or "❌ Not set")
    print("Google Service File:", os.path.basename(GOOGLE_CREDS))
    print("Sheets IDs:",
          bool(SPREADSHEET_GUEST_ASSIST_ID),
          bool(SPREADSHEET_HOTEL_CONTACTS_ID),
          bool(SPREADSHEET_NOTIFICATIONSLOG_ID))
    print("Twilio Config:", "✅ Present" if TWILIO_ACCOUNT_SID else "❌ Not set")
    print("-----------------------------\n")
