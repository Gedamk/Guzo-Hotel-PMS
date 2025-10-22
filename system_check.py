# -*- coding: utf-8 -*-
"""
system_check.py – Guzo Guest Assist System Health Checker
---------------------------------------------------------
Performs environment and connectivity tests for all key APIs.
Logs results into logs/system_events.log.
"""

import os
import requests
import asyncio
from datetime import datetime
from dotenv import find_dotenv, load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from telegram import Bot

# === Helper: Write to logs/system_events.log ===
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_events.log")

def log_event(module: str, status: str, message: str):
    """Append an event log line to system_events.log and print to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {module} | {status} | {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

# === Step 1: Load .env ===
env_path = find_dotenv(usecwd=True)
if not env_path:
    print("❌ No .env file found.")
    log_event("system_check", "ERROR", "No .env file detected")
    exit()

load_dotenv(env_path, override=True)
print(f"✅ Loaded .env from: {env_path}\n")

# === Step 2: Test SendGrid ===
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")
if SENDGRID_KEY:
    print(f"SendGrid key detected (len={len(SENDGRID_KEY)})")
    log_event("system_check", "OK", "SendGrid key loaded successfully")
else:
    print("❌ SENDGRID_API_KEY not found")
    log_event("system_check", "ERROR", "Missing SendGrid key")

# === Step 3: Test Twilio ===
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

if ACCOUNT_SID and AUTH_TOKEN:
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        account = client.api.accounts(ACCOUNT_SID).fetch()
        print(f"Twilio connection OK: {account.friendly_name}")
        log_event("system_check", "OK", "Twilio API connected successfully")
    except Exception as e:
        print(f"❌ Twilio error: {e}")
        log_event("system_check", "ERROR", f"Twilio test failed: {e}")
else:
    print("❌ Twilio credentials missing")
    log_event("system_check", "ERROR", "Missing Twilio credentials")

# === Step 4: Test Telegram Bot ===
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if BOT_TOKEN:
    try:
        from telegram import Bot

        async def check_bot():
            bot = Bot(token=BOT_TOKEN)
            info = await bot.get_me()
            print(f"Telegram Bot connected: {info.username}")
            log_event("system_check", "OK", f"Telegram bot connected: {info.username}")

        asyncio.get_event_loop().run_until_complete(check_bot())

    except Exception as e:
        print(f"❌ Telegram error: {e}")
        log_event("system_check", "ERROR", f"Telegram test failed: {e}")
else:
    print("❌ TELEGRAM_BOT_TOKEN not found")
    log_event("system_check", "ERROR", "Missing Telegram bot token")

# === Step 5: Test Google Sheets ===
SERVICE_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if SERVICE_JSON and os.path.exists(SERVICE_JSON):
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_JSON, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        print("Google Sheets API connected successfully")
        log_event("system_check", "OK", "Google Sheets API connected successfully")
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        log_event("system_check", "ERROR", f"Google Sheets test failed: {e}")
else:
    print("❌ Google credentials not found or invalid path")
    log_event("system_check", "ERROR", "Missing or invalid Google credentials")

# === Step 6: Test Weather API ===
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = os.getenv("CITY", "Addis Ababa")
if WEATHER_KEY:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print(f"Weather API OK for {CITY}")
            log_event("system_check", "OK", f"Weather API working for {CITY}")
        else:
            raise Exception(f"HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Weather API error: {e}")
        log_event("system_check", "ERROR", f"Weather API failed: {e}")
else:
    print("❌ OPENWEATHER_API_KEY not found")
    log_event("system_check", "ERROR", "Missing Weather API key")

# === Step 7: Test Flights API ===
FLIGHTS_KEY = os.getenv("AVIATIONSTACK_API_KEY")
if FLIGHTS_KEY:
    try:
        url = f"http://api.aviationstack.com/v1/flights?access_key={FLIGHTS_KEY}&limit=1"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print("Flights API reachable")
            log_event("system_check", "OK", "Flights API reachable")
        else:
            raise Exception(f"HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Flights API error: {e}")
        log_event("system_check", "ERROR", f"Flights API failed: {e}")
else:
    print("❌ AVIATIONSTACK_API_KEY not found")
    log_event("system_check", "ERROR", "Missing Flights API key")

print("\n✅ System check complete – results logged to logs/system_events.log")
# -*- coding: utf-8 -*-
"""
system_check.py – Guzo Guest Assist System Health Checker
---------------------------------------------------------
Performs environment and connectivity tests for all key APIs.
Logs results into logs/system_events.log.
"""

import os
import requests
import asyncio
from datetime import datetime
from dotenv import find_dotenv, load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from telegram import Bot

# === Helper: Write to logs/system_events.log ===
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_events.log")

def log_event(module: str, status: str, message: str):
    """Append an event log line to system_events.log and print to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {module} | {status} | {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

# === Step 1: Load .env ===
env_path = find_dotenv(usecwd=True)
if not env_path:
    print("❌ No .env file found.")
    log_event("system_check", "ERROR", "No .env file detected")
    exit()

load_dotenv(env_path, override=True)
print(f"✅ Loaded .env from: {env_path}\n")

# === Step 2: Test SendGrid ===
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")
if SENDGRID_KEY:
    print(f"SendGrid key detected (len={len(SENDGRID_KEY)})")
    log_event("system_check", "OK", "SendGrid key loaded successfully")
else:
    print("❌ SENDGRID_API_KEY not found")
    log_event("system_check", "ERROR", "Missing SendGrid key")

# === Step 3: Test Twilio ===
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

if ACCOUNT_SID and AUTH_TOKEN:
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        account = client.api.accounts(ACCOUNT_SID).fetch()
        print(f"Twilio connection OK: {account.friendly_name}")
        log_event("system_check", "OK", "Twilio API connected successfully")
    except Exception as e:
        print(f"❌ Twilio error: {e}")
        log_event("system_check", "ERROR", f"Twilio test failed: {e}")
else:
    print("❌ Twilio credentials missing")
    log_event("system_check", "ERROR", "Missing Twilio credentials")

# === Step 4: Test Telegram Bot ===
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if BOT_TOKEN:
    try:
        from telegram import Bot

        async def check_bot():
            bot = Bot(token=BOT_TOKEN)
            info = await bot.get_me()
            print(f"Telegram Bot connected: {info.username}")
            log_event("system_check", "OK", f"Telegram bot connected: {info.username}")

        asyncio.get_event_loop().run_until_complete(check_bot())

    except Exception as e:
        print(f"❌ Telegram error: {e}")
        log_event("system_check", "ERROR", f"Telegram test failed: {e}")
else:
    print("❌ TELEGRAM_BOT_TOKEN not found")
    log_event("system_check", "ERROR", "Missing Telegram bot token")

# === Step 5: Test Google Sheets ===
SERVICE_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if SERVICE_JSON and os.path.exists(SERVICE_JSON):
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_JSON, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        print("Google Sheets API connected successfully")
        log_event("system_check", "OK", "Google Sheets API connected successfully")
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        log_event("system_check", "ERROR", f"Google Sheets test failed: {e}")
else:
    print("❌ Google credentials not found or invalid path")
    log_event("system_check", "ERROR", "Missing or invalid Google credentials")

# === Step 6: Test Weather API ===
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = os.getenv("CITY", "Addis Ababa")
if WEATHER_KEY:
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print(f"Weather API OK for {CITY}")
            log_event("system_check", "OK", f"Weather API working for {CITY}")
        else:
            raise Exception(f"HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Weather API error: {e}")
        log_event("system_check", "ERROR", f"Weather API failed: {e}")
else:
    print("❌ OPENWEATHER_API_KEY not found")
    log_event("system_check", "ERROR", "Missing Weather API key")

# === Step 7: Test Flights API ===
FLIGHTS_KEY = os.getenv("AVIATIONSTACK_API_KEY")
if FLIGHTS_KEY:
    try:
        url = f"http://api.aviationstack.com/v1/flights?access_key={FLIGHTS_KEY}&limit=1"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print("Flights API reachable")
            log_event("system_check", "OK", "Flights API reachable")
        else:
            raise Exception(f"HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Flights API error: {e}")
        log_event("system_check", "ERROR", f"Flights API failed: {e}")
else:
    print("❌ AVIATIONSTACK_API_KEY not found")
    log_event("system_check", "ERROR", "Missing Flights API key")

print("\n✅ System check complete – results logged to logs/system_events.log")

