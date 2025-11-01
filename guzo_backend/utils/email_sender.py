# -*- coding: utf-8 -*-
"""
email_sender.py
Handles sending notifications through Gmail.
"""

import smtplib
from email.mime.text import MIMEText
import os

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_notification(subject: str, body: str):
    """Send a plain-text email notification using Gmail."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[WARN] Email credentials not found in environment variables.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS  # self-notify

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("[EMAIL] Notification sent successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
