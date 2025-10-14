# -*- coding: utf-8 -*-
"""
send_message.py
-------------------------------------------------------
Multi-channel message sender for Guzo Guest Assist.
Automatically selects Telegram, WhatsApp, Email, or SMS
based on available hotel contact data.
-------------------------------------------------------
Dependencies:
- requests
- twilio
- sendgrid
- googleapiclient
- pandas
"""

import os
import requests
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from guzo_booking_bot.utils.hotel_directory import fetch_hotel_data
from guzo_booking_bot.utils.channel_selector import select_best_channel

# ✅ Force-load environment variables from your main project folder
dotenv_path = os.path.join("C:\\Users\\Gedan\\Desktop\\Guzo", ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"🔑 Loaded environment file: {dotenv_path}")
else:
    print(f"⚠️ .env file not found at: {dotenv_path}")

# ==============🔐 ENVIRONMENT VARIABLES ===================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
TWILIO_SMS_FROM = os.getenv("TWILIO_SMS_FROM")
DEFAULT_SENDER_EMAIL = os.getenv("DEFAULT_SENDER_EMAIL", "noreply@guzoassist.com")
# ==========================================================


def send_telegram(username, message):
    """Send message via Telegram username (@username)."""
    try:
        if not TELEGRAM_BOT_TOKEN:
            print("⚠️ TELEGRAM_BOT_TOKEN missing in .env")
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": username, "text": message}
        response = requests.post(url, data=data)

        if response.status_code == 200:
            print(f"📨 Telegram message sent to {username}")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Telegram send error: {e}")
        return False


def send_whatsapp(phone, message):
    """Send message via WhatsApp using Twilio."""
    try:
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
            print("⚠️ Twilio WhatsApp credentials missing.")
            return False

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_FROM}",
            body=message,
            to=f"whatsapp:{phone}"
        )
        print(f"📨 WhatsApp sent to {phone}: SID {msg.sid}")
        return True

    except Exception as e:
        print(f"❌ WhatsApp send error: {e}")
        return False


def send_email(recipient, subject, message):
    """Send email using SendGrid."""
    try:
        if not SENDGRID_API_KEY:
            print("⚠️ SENDGRID_API_KEY missing.")
            return False

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        mail = Mail(
            from_email=DEFAULT_SENDER_EMAIL,
            to_emails=recipient,
            subject=subject,
            html_content=f"<p>{message}</p>"
        )
        response = sg.send(mail)
        print(f"📨 Email sent to {recipient}, status {response.status_code}")
        return True

    except Exception as e:
        print(f"❌ Email send error: {e}")
        return False


def send_sms(phone, message):
    """Send fallback SMS using Twilio."""
    try:
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_SMS_FROM):
            print("⚠️ Twilio SMS credentials missing.")
            return False

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_SMS_FROM,
            body=message,
            to=phone
        )
        print(f"📨 SMS sent to {phone}: SID {msg.sid}")
        return True

    except Exception as e:
        print(f"❌ SMS send error: {e}")
        return False


def send_multi_channel(hotel_row, message):
    """Decide best channel and send the message."""
    choice = select_best_channel(hotel_row)
    channel = choice["type"]
    contact = choice["value"]

    if channel == "telegram":
        return send_telegram(contact, message)

    elif channel == "whatsapp":
        return send_whatsapp(contact, message)

    elif channel == "email":
        subject = f"Message from Guzo Guest Assist - {hotel_row.get('Hotel Name', '')}"
        return send_email(contact, subject, message)

    elif channel == "sms":
        return send_sms(contact, message)

    elif channel == "website":
        print(f"🌐 No direct channel, please contact via website: {contact}")
        return True

    else:
        print("⚠️ No available contact channel for this hotel.")
        return False


# 🧪 Optional: test the system directly
if __name__ == "__main__":
    hotels_df = fetch_hotel_data()
    message = "👋 Hello from Guzo Guest Assist! This is a multi-channel system test."

    for _, hotel in hotels_df.iterrows():
        print(f"\n🏨 Sending message to {hotel.get('Hotel Name', 'Unknown')}")
        send_multi_channel(hotel, message)
