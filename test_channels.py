# -*- coding: utf-8 -*-
"""
Quick diagnostic tool for all Guzo communication channels (plain text version).
"""

import os, requests, json
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

load_dotenv(dotenv_path=".env", override=True)

print("\n--- Testing all communication channels ---\n")

# ---- Google Sheets ----
try:
    scope =scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

    creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scope)
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SHEET_NAME")).sheet1
    print("Google Sheets: OK")
except Exception as e:
    print("Google Sheets error:", e)

# ---- SendGrid Email ----
try:
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    message = Mail(
        from_email=os.getenv("SENDER_EMAIL"),
        to_emails=os.getenv("SENDER_EMAIL"),
        subject="Guzo Guest Assist Test Email",
        html_content="This is a test message from Guzo Guest Assist dashboard.")
    sg.send(message)
    print("SendGrid Email: OK")
except Exception as e:
    print("SendGrid Email error:", e)

# ---- Telegram Bot ----
try:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        url = f"https://api.telegram.org/bot{token}/getMe"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            print("Telegram Bot: OK")
        else:
            print("Telegram Bot error:", r.text)
    else:
        print("Telegram Bot token missing.")
except Exception as e:
    print("Telegram Bot error:", e)

# ---- Weather API ----
try:
    key = os.getenv("OPENWEATHER_API_KEY")
    city = os.getenv("CITY", "Addis Ababa")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        print("Weather API: OK")
    else:
        print("Weather API error:", r.text)
except Exception as e:
    print("Weather API error:", e)

# ---- Flights API ----
try:
    key = os.getenv("AVIATIONSTACK_API_KEY")
    url = f"http://api.aviationstack.com/v1/flights?access_key={key}&limit=1"
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        print("Flights API: OK")
    else:
        print("Flights API error:", r.text)
except Exception as e:
    print("Flights API error:", e)

# ---- Twilio SMS ----
try:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_PHONE_NUMBER")
    to_ = os.getenv("SUPPORT_PHONE", "+251987006170")
    client = Client(sid, auth)
    msg = client.messages.create(body="Guzo Guest Assist test SMS", from_=from_, to=to_)
    print("Twilio SMS: OK (SID:", msg.sid, ")")
except Exception as e:
    print("Twilio SMS error:", e)

print("\n--- Channel test complete ---\n")
