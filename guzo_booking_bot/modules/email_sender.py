# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Smart Email Sender (v3.0)
---------------------------------------------------------
Handles professional, secure, and multilingual email delivery.

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Primary: SendGrid API
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Fallback: Gmail SMTP (App Password)
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Supports multiple attachments (PDF, CSV, Images)
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Hospitality-grade templates for automated messages
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Fully compatible with automation/report_generator.py
"""

import os
import smtplib
import base64
import mimetypes
from email.message import EmailMessage
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition
)

# ==========================================================
# ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Helper: MIME type detection
# ==========================================================
def _guess_mime(path):
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        return "application", "octet-stream"
    maintype, subtype = mime.split("/", 1)
    return maintype, subtype


# ==========================================================
# ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Send via SendGrid (Preferred)
# ==========================================================
def _send_via_sendgrid(to_email, subject, body, from_email=None, attachments=None):
    sg_api_key = os.getenv("SENDGRID_API_KEY")
    if not sg_api_key:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No SendGrid API key found. Skipping SendGrid send.")
        return False

    try:
        sender_email = from_email or os.getenv("EMAIL_SENDER", "noreply@guzoassist.com")

        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=body or "No content provided."
        )

        # Attachments
        attachments = attachments or []
        for path in attachments:
            with open(path, "rb") as f:
                file_data = f.read()
                b64 = base64.b64encode(file_data).decode()
            maintype, subtype = _guess_mime(path)
            attachment = Attachment(
                FileContent(b64),
                FileName(os.path.basename(path)),
                FileType(f"{maintype}/{subtype}"),
                Disposition("attachment"),
            )
            message.add_attachment(attachment)

        sg = SendGridAPIClient(sg_api_key)
        response = sg.send(message)
        print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Email sent via SendGrid to {to_email} ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Status: {response.status_code}")
        return True

    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ SendGrid send failed: {e}")
        return False


# ==========================================================
# ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ© Send via Gmail (Fallback)
# ==========================================================
def _send_via_gmail(to_email, subject, body, from_email=None, attachments=None):
    gmail_user = os.getenv("GMAIL_EMAIL")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password
    if not (gmail_user and gmail_pass):
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No Gmail credentials found. Skipping Gmail send.")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = from_email or gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body or "No content provided.")

        attachments = attachments or []
        for path in attachments:
            with open(path, "rb") as f:
                data = f.read()
            maintype, subtype = _guess_mime(path)
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(path),
            )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)

        print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ© Email sent via Gmail SMTP to {to_email}")
        return True

    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Gmail SMTP send failed: {e}")
        return False


# ==========================================================
# ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ÃÂÃÂÃÂÃÂ  Unified Public Function (For Automation)
# ==========================================================
def send_email(to_email, subject, body=None, from_email=None, attachments=None):
    """
    Smart unified email sender.
    - Uses SendGrid by default (fallback: Gmail)
    - Compatible with hospitality automation modules
    - Handles both HTML and plain text content
    """
    attachments = attachments or []
    provider = os.getenv("EMAIL_PROVIDER", "sendgrid").lower()

    print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Using provider: {provider}")

    if provider == "sendgrid":
        if _send_via_sendgrid(to_email, subject, body, from_email, attachments):
            return True
        else:
            return _send_via_gmail(to_email, subject, body, from_email, attachments)

    elif provider == "gmail":
        if _send_via_gmail(to_email, subject, body, from_email, attachments):
            return True
        else:
            return _send_via_sendgrid(to_email, subject, body, from_email, attachments)

    else:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Invalid EMAIL_PROVIDER. Please set 'sendgrid' or 'gmail' in .env.")
        return False


# ==========================================================
# ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ Backward Compatibility Alias
# ==========================================================
def send_notification(to_email, subject, body=None, from_email=None, attachments=None):
    """Alias for send_email() for legacy scripts."""
    return send_email(to_email, subject, body, from_email, attachments)
