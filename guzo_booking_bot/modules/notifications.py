"""
Notifications Module
- Handles Email, SMS, WhatsApp, Telegram, and Viber sending
- Logs every notification attempt to Google Sheets (audit trail)
"""

import logging
from guzo_booking_bot import config as cfg
from guzo_booking_bot.modules.notification_log import log_notification

# External services
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import requests

logger = logging.getLogger(__name__)

# -----------------------
# Email
# -----------------------

def send_email(to_email: str, subject: str, body: str, guest_name: str = "Unknown"):
    """Send email using SendGrid or Gmail fallback"""
    try:
        if cfg.EMAIL_PROVIDER == "sendgrid" and cfg.SENDGRID_API_KEY:
            message = Mail(
                from_email=(cfg.SENDGRID_SENDER_EMAIL, cfg.SENDGRID_SENDER_NAME),
                to_emails=to_email,
                subject=subject,
                plain_text_content=body,
            )
            sg = SendGridAPIClient(cfg.SENDGRID_API_KEY)
            sg.send(message)
            log_notification(guest_name, to_email, "Email", "SUCCESS")
            return True

        elif cfg.EMAIL_PROVIDER == "gmail" and cfg.GMAIL_EMAIL and cfg.GMAIL_PASSWORD:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = cfg.GMAIL_EMAIL
            msg["To"] = to_email

            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(cfg.GMAIL_EMAIL, cfg.GMAIL_PASSWORD)
            server.sendmail(cfg.GMAIL_EMAIL, [to_email], msg.as_string())
            server.quit()
            log_notification(guest_name, to_email, "Email", "SUCCESS")
            return True

        else:
            raise Exception("No email provider configured")

    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        log_notification(guest_name, to_email, "Email", "FAILED", str(e))
        return False


# -----------------------
# SMS
# -----------------------

def send_sms(to_phone: str, message: str, guest_name: str = "Unknown"):
    """Send SMS via Twilio"""
    try:
        client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=cfg.TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        log_notification(guest_name, to_phone, "SMS", "SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ SMS failed: {e}")
        log_notification(guest_name, to_phone, "SMS", "FAILED", str(e))
        return False


# -----------------------
# WhatsApp
# -----------------------

def send_whatsapp(to_phone: str, message: str, guest_name: str = "Unknown"):
    """Send WhatsApp message via Twilio"""
    try:
        client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=cfg.TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_phone}"
        )
        log_notification(guest_name, to_phone, "WhatsApp", "SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ WhatsApp failed: {e}")
        log_notification(guest_name, to_phone, "WhatsApp", "FAILED", str(e))
        return False


# -----------------------
# Telegram
# -----------------------

def send_telegram(chat_id: str, message: str, guest_name: str = "Unknown"):
    """Send Telegram message via Bot API"""
    try:
        url = f"https://api.telegram.org/bot{cfg.TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": chat_id, "text": message})
        if resp.status_code == 200:
            log_notification(guest_name, chat_id, "Telegram", "SUCCESS")
            return True
        else:
            raise Exception(resp.text)
    except Exception as e:
        logger.error(f"❌ Telegram failed: {e}")
        log_notification(guest_name, chat_id, "Telegram", "FAILED", str(e))
        return False


# -----------------------
# Viber (Placeholder)
# -----------------------

def send_viber(to_phone: str, message: str, guest_name: str = "Unknown"):
    """Send Viber message (placeholder for real API integration)"""
    try:
        if not cfg.VIBER_API_KEY:
            raise Exception("No Viber API key configured")

        # Example placeholder API call
        logger.info(f"📤 Sending Viber message to {to_phone}: {message}")
        log_notification(guest_name, to_phone, "Viber", "SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ Viber failed: {e}")
        log_notification(guest_name, to_phone, "Viber", "FAILED", str(e))
        return False
