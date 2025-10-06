# guzo_booking_bot/modules/sms_sender.py
"""
SMS Sender Module
Handles sending SMS via Twilio with hospitality-focused error handling.
"""

import os
from twilio.rest import Client
from guzo_booking_bot import config

# Twilio setup
ACCOUNT_SID = config.TWILIO_ACCOUNT_SID
AUTH_TOKEN = config.TWILIO_AUTH_TOKEN
FROM_NUMBER = config.TWILIO_PHONE_NUMBER

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms(to_number, message):
    """
    Send SMS to a guest.
    Best practice: personalize and include booking context.
    """
    try:
        if not to_number.startswith("+"):
            # Auto-add Ethiopia country code if missing
            to_number = f"+251{to_number}" if len(to_number) == 9 else f"+{to_number}"

        msg = client.messages.create(
            body=message,
            from_=FROM_NUMBER,
            to=to_number
        )
        print(f"✅ SMS sent to {to_number}, SID: {msg.sid}")
        return msg.sid

    except Exception as e:
        print(f"❌ Failed to send SMS to {to_number}: {e}")
        raise
