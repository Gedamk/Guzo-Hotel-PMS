# -*- coding: utf-8 -*-
"""
Simple Twilio WhatsApp test for Guzo Guest Assist
-------------------------------------------------
Sends a test message using your Twilio account to confirm WhatsApp/SMS channel works.
"""

import os
from twilio.rest import Client
from dotenv import load_dotenv

# === Explicitly load the .env file (absolute Windows path) ===
env_path = r"C:\Users\Gedan\Desktop\Guzo\.env"
if not os.path.exists(env_path):
    print(f"❌ .env file not found at {env_path}")
    exit()

load_dotenv(dotenv_path=env_path)
print(f"✅ Loaded environment from: {env_path}")

# === Twilio credentials ===
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TO_NUMBER = os.getenv("SUPPORT_PHONE")

print("\n🔍 Checking Twilio credentials...")
if not all([ACCOUNT_SID, AUTH_TOKEN, FROM_NUMBER, TO_NUMBER]):
    print("❌ Missing Twilio variables. Please verify .env file:")
    print(f"  SID={ACCOUNT_SID}")
    print(f"  FROM={FROM_NUMBER}")
    print(f"  TO={TO_NUMBER}")
    exit()

# === Show token prefix to confirm load ===
print(f"Account SID configured: {bool(ACCOUNT_SID)}")
print(f"Auth Token configured: {bool(AUTH_TOKEN)}")

try:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    print(f"\n📨 Sending WhatsApp message from {FROM_NUMBER} to {TO_NUMBER} ...")

    message = client.messages.create(
        body="Guzo Guest Assist WhatsApp Test ✅ - Live system verification.",
        from_=FROM_NUMBER,
        to=TO_NUMBER
    )

    print(f"✅ Message sent successfully! SID: {message.sid}")

except Exception as e:
    print(f"\n❌ Twilio Error:\n{e}")
    print("\n💡 Troubleshooting:")
    print(" - Make sure Account SID and Auth Token are copied correctly.")
    print(" - If still failing, regenerate the Auth Token in your Twilio console:")
    print("   https://www.twilio.com/console/project/settings")
