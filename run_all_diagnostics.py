# -*- coding: utf-8 -*-
"""
Comprehensive Diagnostic for Guzo Guest Assist
----------------------------------------------
Checks all environment variables, dependencies, and API connections.
Logs detailed results to logs/system_health.log
"""

import os, importlib, requests
from datetime import datetime
from dotenv import load_dotenv

# --- Setup ---
LOG_PATH = "logs/system_health.log"
os.makedirs("logs", exist_ok=True)

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {msg}\n")

print("\nRunning Guzo System Diagnostics...\n")

# --- 1️⃣ Load Environment ---
dotenv_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    log(f"✅ Environment loaded from {dotenv_path}")
else:
    log("❌ .env file not found — please create one from .env.example")

required_vars = [
    "SENDGRID_API_KEY", "SENDER_EMAIL", "TELEGRAM_BOT_TOKEN",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
    "OPENWEATHER_API_KEY", "AVIATIONSTACK_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS"
]
for key in required_vars:
    log(f"{key}: {'✅ Loaded' if os.getenv(key) else '❌ MISSING'}")

# --- 2️⃣ Check Python Modules ---
modules = [
    "streamlit", "gspread", "sendgrid", "twilio",
    "requests", "pandas", "dotenv"
]
for m in modules:
    try:
        importlib.import_module(m)
        log(f"✅ Module OK: {m}")
    except ImportError:
        log(f"❌ Missing module: {m}")

# --- 3️⃣ Google Sheets ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    client.open(os.getenv("SHEET_NAME", "Guest_Bookings"))
    log("✅ Google Sheets connection successful")
except Exception as e:
    log(f"❌ Google Sheets error: {e}")

# --- 4️⃣ Weather API ---
try:
    key = os.getenv("OPENWEATHER_API_KEY")
    city = os.getenv("CITY", "Addis Ababa")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        log("✅ Weather API connected successfully")
    else:
        log(f"❌ Weather API failed: {r.text}")
except Exception as e:
    log(f"❌ Weather API error: {e}")

log("\n✅ Diagnostics complete — see logs/system_health.log\n")
