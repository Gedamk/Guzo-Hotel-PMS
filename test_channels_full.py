# -*- coding: utf-8 -*-
# ======================================================
# Guzo Guest Assist - Full Communication Test (Clean UTF-8)
# Tests: SendGrid Email + Twilio WhatsApp
# ======================================================
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from dotenv import load_dotenv

# === Load environment ===
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env")

# === Load variables ===
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE")

print("\n====================================")
print("GUZO COMMUNICATION CHANNEL TEST")
print("====================================")

# ======================================================
# 1) TEST SENDGRID EMAIL
# ======================================================
print("\nTesting SendGrid Email...")

try:
    if not SENDGRID_API_KEY or not SENDER_EMAIL:
        raise Exception("Missing SendGrid credentials")

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails="yourpersonalemail@gmail.com",  # <-- replace with your real email
        subject="Guzo Guest Assist – Combined Channel Test",
        html_content=(
            "<h3>Guzo Guest Assist Communication Test</h3>"
            "<p>This is a combined test message from the Guzo system.</p>"
            "<p>If you received this email, the SendGrid channel is working.</p>"
        ),
    )
    response = sg.send(message)
    print(f"Email sent successfully! Status code: {response.status_code}")

except Exception as e:
    print(f"Email failed: {e}")


# ======================================================
# 2) TEST TWILIO WHATSAPP
# ======================================================
print("\nTesting Twilio WhatsApp...")

try:
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, SUPPORT_PHONE]):
        raise Exception("Missing Twilio environment variables")

    client = Client(TWILIO_SID, TWILIO_TOKEN)
    message = client.messages.create(
        body="Guzo Guest Assist WhatsApp Test - If you see this, Twilio is working!",
        from_=TWILIO_FROM,
        to=SUPPORT_PHONE
    )
    print(f"WhatsApp message sent successfully! SID: {message.sid}")

except Exception as e:
    print(f"WhatsApp test failed: {e}")


# ======================================================
# FINAL SUMMARY
# ======================================================
print("\n====================================")
print("TEST COMPLETE")
print("====================================")
print("Check your WhatsApp and Email inbox for test messages.")
print("====================================\n")
