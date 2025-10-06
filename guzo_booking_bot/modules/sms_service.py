"""
SMS Service Module
Handles sending SMS notifications to guests and hotels.
"""

import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load secrets from .env
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms(to: str, message: str):
    """Send SMS using Twilio API."""
    try:
        sms = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to
        )
        print(f"✅ SMS sent to {to}, SID: {sms.sid}")
        return True
    except Exception as e:
        print(f"❌ SMS failed for {to}: {e}")
        return False

if __name__ == "__main__":
    # Test SMS
    send_sms("+11234567890", "Hello from Guzo Guest Assist 🚀")
