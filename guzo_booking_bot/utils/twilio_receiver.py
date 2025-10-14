# -*- coding: utf-8 -*-
"""
twilio_receiver.py
Handles incoming SMS and WhatsApp booking messages via Twilio API.
"""

import os
from twilio.rest import Client
from guzo_booking_bot.utils.sheet_logger import log_message
from guzo_booking_bot.utils.email_sender import send_notification
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
SMS_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
WA_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def receive_message(from_number: str, message: str, channel: str = "sms"):
    """Simulate incoming SMS/WhatsApp message."""
    log_message(channel, from_number, message)
    print(f"[{channel.upper()}] New message from {from_number}: {message}")

    # Send confirmation back to sender
    confirmation = "✅ Your booking request has been received. We'll get back to you shortly."
    send_reply(from_number, confirmation, channel)

def send_reply(to_number: str, message: str, channel: str = "sms"):
    """Send confirmation via Twilio SMS or WhatsApp."""
    try:
        if channel == "whatsapp":
            from_num = WA_NUMBER
            to_num = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
        else:
            from_num = SMS_NUMBER
            to_num = to_number

        client.messages.create(
            from_=from_num,
            to=to_num,
            body=message
        )
        print(f"[{channel.upper()}] Confirmation sent to {to_number}")
    except Exception as e:
        print(f"[ERROR] Failed to send {channel} message: {e}")

if __name__ == "__main__":
    print("[DEBUG] Twilio Receiver Test Running...")
    test_number = input("Enter test phone number (e.g. +15551234567): ")
    test_message = input("Enter test message: ")
    receive_message(test_number, test_message, channel="sms")
