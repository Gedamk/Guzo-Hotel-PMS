# -*- coding: utf-8 -*-
"""
Email Sender Module
Centralized notification system using SendGrid (primary)
with Gmail fallback for resilience.
Adds multilingual support and manager alerts.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


# ==============================
# CONFIGURATION
# ==============================
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@guzoassist.com")

# Gmail fallback
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")


# ==============================
# CORE SEND FUNCTION
# ==============================
def send_email_sendgrid(to_email: str, subject: str, content: str):
    """Send email via SendGrid API."""
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[OK] Email sent via SendGrid to {to_email}, status: {response.status_code}")
        return True
    except Exception as e:
        print(f"[FAIL] SendGrid failed: {e}")
        return False


def send_email_gmail(to_email: str, subject: str, content: str):
    """Send email via Gmail SMTP fallback."""
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"[OK] Email sent via Gmail to {to_email}")
        return True
    except Exception as e:
        print(f"[FAIL] Gmail fallback failed: {e}")
        return False


# ==============================
# UNIFIED NOTIFICATION HANDLER
# ==============================
def send_notification(to_email: str, subject: str, content: str, lang: str = "en"):
    """
    Unified email sender with multilingual support and resilience.
    
    Args:
        to_email (str): recipient email
        subject (str): email subject
        content (str): plain text body
        lang (str): language code ("en", "am", "om")
    """

    # Add multilingual footer
    translations = {
        "en": "\n\nThank you,\nGuzo Guest Assist",
        "am": "\n\nእናመሰግናለን፣\nጉዞ ጎረቤት እገዛ",
        "om": "\n\nGalatoomi,\nGuzo Guest Assist",
    }
    footer = translations.get(lang, translations["en"])
    body = f"{content}{footer}"

    # Try SendGrid first, fallback to Gmail
    if SENDGRID_API_KEY and send_email_sendgrid(to_email, subject, body):
        return True
    elif GMAIL_USER and GMAIL_PASSWORD:
        return send_email_gmail(to_email, subject, body)
    else:
        print("❌ No email provider configured.")
        return False
