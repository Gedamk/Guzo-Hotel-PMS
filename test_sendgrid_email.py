# -*- coding: utf-8 -*-
# ======================================================
# Guzo Guest Assist - SendGrid Email Test (UTF-8 Safe)
# ======================================================
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load .env file (absolute path for Windows)
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env")

# === Email configuration ===
sender = os.getenv("SENDER_EMAIL")
receiver = "yourpersonalemail@gmail.com"  # <-- Replace with your real email

print("Checking SendGrid credentials...")
api_key = os.getenv("SENDGRID_API_KEY")
if not api_key or not sender:
    print("❌ Missing SENDGRID_API_KEY or SENDER_EMAIL in .env")
    exit()

# === Email content ===
message = Mail(
    from_email=sender,
    to_emails=receiver,
    subject="Guzo Guest Assist – Email Test ✅",
    html_content=(
        "<h3>Hello from Guzo Guest Assist</h3>"
        "<p>This is a live SendGrid test to confirm your email integration works.</p>"
        "<p>— Guzo System</p>"
    )
)

# === Send email ===
try:
    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    print(f"✅ Email sent successfully! Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Email failed: {e}")
