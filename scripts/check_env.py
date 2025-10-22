# -*- coding: utf-8 -*-
"""
Guzo Guest Assist - Environment Configuration Checker
-----------------------------------------------------
Checks all core communication credentials and configurations:
- Google Sheets
- SendGrid
- Twilio (WhatsApp)
- Telegram Bot
- Gmail fallback
"""

import os
from dotenv import load_dotenv

# Dynamically locate .env in project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
env_path = os.path.join(ROOT_DIR, ".env")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print("\n==============================")
    print("🌍 GUZO GUEST ASSIST - SYSTEM CHECK")
    print("==============================\n")
else:
    print(f"❌ .env file not found at {env_path}")
    exit(1)

def check_env_var(key, must_exist=True, length=None, hint=None):
    value = os.getenv(key)
    if not value:
        if must_exist:
            print(f"⚠️  {key} is missing. {hint or ''}")
        return False
    if length and len(value) < length:
        print(f"⚠️  {key} looks invalid (too short). {hint or ''}")
        return False
    print(f"✅ {key} found.")
    return True

def check_file(path, desc):
    if os.path.exists(path):
        print(f"✅ {desc} found at: {path}")
        return True
    else:
        print(f"⚠️  {desc} missing at: {path}")
        return False

# === GOOGLE SHEETS ===
print("📄 GOOGLE SHEETS API:")
check_file(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""), "Google credentials JSON file")
check_env_var("GOOGLE_SHEET_ID_GUEST_ASSIST", False)
check_env_var("GOOGLE_SHEET_ID_HOTEL_CONTACTS", False)

# === SENDGRID ===
print("\n✉️  SENDGRID:")
check_env_var("SENDGRID_API_KEY", True, 30, "Set your API key from https://app.sendgrid.com/settings/api_keys")
check_env_var("FROM_EMAIL", True, 5, "Set your verified sender email address.")

# === TWILIO ===
print("\n💬 TWILIO WHATSAPP:")
check_env_var("TWILIO_ACCOUNT_SID", True, 30, "Copy from https://www.twilio.com/console")
check_env_var("TWILIO_AUTH_TOKEN", True, 30, "Copy the real Auth Token (not 'your...')")
check_env_var("TWILIO_PHONE_NUMBER", True, 5, "Example: whatsapp:+14155238886")
check_env_var("SUPPORT_PHONE", True, 5, "Example: whatsapp:+251987006170")

# === TELEGRAM ===
print("\n🤖 TELEGRAM BOT:")
check_env_var("TELEGRAM_TOKEN", True, 20, "Get from @BotFather using /token")

# === GMAIL FALLBACK ===
print("\n📧 GMAIL BACKUP:")
check_env_var("GMAIL_USER", True, 5, "Example: yourname@gmail.com")
check_env_var("GMAIL_PASSWORD", True, 16, "Must be a 16-character App Password from https://myaccount.google.com/apppasswords")

# === SUMMARY ===
print("\n🏁 Environment check complete.\n")
print("✅ If all above show 'found' or valid, your communication system is ready.")
print("⚠️  Any warnings indicate missing or incorrect credentials.\n")
