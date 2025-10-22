# -*- coding: utf-8 -*-
"""
Email Sender Module
-------------------
Sends confirmation and notification emails via SendGrid or Gmail fallback.
Now automatically logs all sent emails to Notifications Log (Google Sheets + SQLite fallback).
"""

import os
import smtplib
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from datetime import datetime

# Import logging function from Google Sheets module
from guzo_booking_bot.modules import google_sheets

load_dotenv()

# === ENVIRONMENT CONFIG ===
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")


# === HELPERS ===
def log_email(to_email, status, method, error_message=""):
    """Add an entry to the Notifications Log (or local DB fallback)."""
    entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Guest Name": to_email.split("@")[0].title(),
        "Guest Type": "standard",
        "Language": "en",
        "Contact": to_email,
        "Channel": method,
        "Status": status,
        "ErrorMessage": error_message,
    }
    google_sheets.add_notification_log(entry)


# === SENDGRID PRIMARY ===
def send_via_sendgrid(to_email, subject, body):
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=body
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ SendGrid: Email sent to {to_email}, status: {response.status_code}")

        # Log successful email
        log_email(to_email, "Sent", "SendGrid")
        return True
    except Exception as e:
        print(f"⚠️ SendGrid failed: {e}")
        log_email(to_email, "Failed", "SendGrid", str(e))
        return False


# === GMAIL FALLBACK ===
def send_via_gmail(to_email, subject, body):
    try:
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"✅ Gmail: Email sent to {to_email}")
        log_email(to_email, "Sent", "Gmail")
        return True
    except Exception as e:
        print(f"❌ Gmail failed: {e}")
        log_email(to_email, "Failed", "Gmail", str(e))
        return False


# === UNIFIED FUNCTION ===
def send_email(to_email, subject, body):
    """
    Sends an email using SendGrid, then Gmail fallback if needed.
    Automatically logs every attempt.
    """
    if not to_email:
        print("⚠️ No recipient email provided.")
        return False

    print(f"📨 Sending confirmation email to {to_email}...")
    if send_via_sendgrid(to_email, subject, body):
        return True
    return send_via_gmail(to_email, subject, body)
