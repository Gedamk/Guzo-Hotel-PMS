# -*- coding: utf-8 -*-
"""
Quick diagnostic tool for all Guzo communication channels (v3.1)
---------------------------------------------------------------
Checks Google Sheets, SendGrid, Telegram, Weather, Flights, and Twilio.
"""

import os, json, requests
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

# ======================================================
# Load Environment
# ======================================================
load_dotenv(dotenv_path=".env", override=True)
print("\n--- Testing all communication channels ---\n")


# ======================================================
# GOOGLE SHEETS (fixed)
# ======================================================
try:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        raise FileNotFoundError("Service account file not found or invalid path.")

    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)

    sheet_name = os.getenv("SHEET_NAME")
    if not sheet_name:
        raise ValueError("Missing SHEET_NAME in .env")

    sheet = client.open(sheet_name).sheet1
    # test read
    _ = sheet.cell(1, 1).value
    print("Google Sheets: OK")
except Exception as e:
    print("Google Sheets error:", e)


# ======================================================
# SENDGRID EMAIL
# ======================================================
try:
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDER_EMAIL")
    to_email = os.getenv("TEST_EMAIL", from_email)

    if not sendgrid_key:
        raise ValueError("Missing SENDGRID_API_KEY in .env")
    if not from_email:
        raise ValueError("Missing SENDER_EMAIL in .env")

    sg = SendGridAPIClient(sendgrid_key)
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="Guzo Guest Assist Test Email",
        html_content="✅ This is a test email from Guzo Guest Assist dashboard."
    )
    response = sg.send(message)
    if response.status_code == 202:
        print("SendGrid Email: OK")
    else:
        print(f"SendGrid Email error: HTTP {response.status_code} → {response.body.decode()}")
except Exception as e:
    print("SendGrid Email error:", e)


# ======================================================
# TELEGRAM BOT
# ======================================================
try:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
    if r.status_code == 200:
        print("Telegram Bot: OK")
    else:
        print("Telegram Bot error:", r.text)
except Exception as e:
    print("Telegram Bot error:", e)


# ======================================================
# WEATHER API
# ======================================================
try:
    weather_key = os.getenv("OPENWEATHER_API_KEY")
    city = os.getenv("CITY", "Addis Ababa")
    if not weather_key:
        raise ValueError("Missing OPENWEATHER_API_KEY in .env")

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_key}&units=metric"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"Weather API: OK ({data['main']['temp']}°C in {city})")
    else:
        print("Weather API error:", r.text)
except Exception as e:
    print("Weather API error:", e)


# ======================================================
# FLIGHTS API
# ======================================================
try:
    flights_key = os.getenv("AVIATIONSTACK_API_KEY") or os.getenv("FLIGHTS_API_KEY")
    if not flights_key:
        raise ValueError("Missing AVIATIONSTACK_API_KEY or FLIGHTS_API_KEY in .env")

    url = f"http://api.aviationstack.com/v1/flights?access_key={flights_key}&limit=1"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        data = r.json()
        if "error" in data:
            print("Flights API error:", json.dumps(data["error"], indent=2))
        else:
            print("Flights API: OK")
    else:
        print("Flights API error:", r.text)
except Exception as e:
    print("Flights API error:", e)


# ======================================================
# TWILIO SMS / WHATSAPP (auto detect)
# ======================================================
try:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_PHONE_NUMBER")
    to_ = os.getenv("SUPPORT_PHONE", "+251987006170")

    if not all([sid, auth, from_, to_]):
        raise ValueError("Missing Twilio credentials or phone numbers in .env")

    client = Client(sid, auth)

    # auto detect WhatsApp vs SMS
    if from_.startswith("whatsapp:") or to_.startswith("whatsapp:"):
        msg = client.messages.create(
            body="📲 Guzo WhatsApp test message successful!",
            from_=from_,
            to=to_
        )
    else:
        msg = client.messages.create(
            body="📲 Guzo SMS test message successful!",
            from_=from_,
            to=to_
        )

    print("Twilio Message: OK (SID:", msg.sid, ")")
except Exception as e:
    print("Twilio SMS error:", e)


print("\n--- Channel test complete ---\n")
