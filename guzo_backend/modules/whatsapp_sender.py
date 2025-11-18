# -*- coding: utf-8 -*-
"""
whatsapp_sender.py – Guzo Guest Assist WhatsApp Message Sender
---------------------------------------------------------------
Handles WhatsApp notifications to guests and hotel managers.

✅ Features:
- UTF-8 clean (no encoding errors)
- Simulated mode for local testing (default)
- Ready for real Twilio or WhatsApp Cloud API integration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# ======================================================
# CONFIGURATION
# ======================================================
USE_TWILIO = os.getenv("USE_TWILIO", "false").lower() == "true"

# Optional Twilio credentials (only needed for live sending)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# ======================================================
# MAIN FUNCTION
# ======================================================
def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message to a given phone number.
    Default behavior: simulated print (safe for testing).
    If USE_TWILIO=True and credentials are valid, sends a real WhatsApp message.
    """
    if USE_TWILIO and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER:
        try:
            from twilio.rest import Client

            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            full_to = f"whatsapp:{to_number}"
            full_from = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
            msg = client.messages.create(from_=full_from, to=full_to, body=message)
            print(f"📱 [WhatsApp] Sent to {to_number}: Message SID {msg.sid}")
            return True

        except Exception as e:
            print(f"⚠️ [WhatsApp] Error sending message via Twilio: {e}")
            return False

    else:
        # Simulated sender for local testing
        print(f"📱 [WhatsApp] (Simulated) Sending to {to_number}: {message}")
        return True

# ======================================================
# SELF-TEST
# ======================================================
if __name__ == "__main__":
    test_number = "+12025550123"
    test_message = "✅ WhatsApp sender test successful."
    send_whatsapp_message(test_number, test_message)
