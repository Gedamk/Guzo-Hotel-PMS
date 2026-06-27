import os
import pywhatkit
import smtplib
from email.mime.text import MIMEText
import requests

# ----- Email Settings -----
EMAIL_ADDRESS = os.getenv("GUZO_EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("GUZO_EMAIL_PASSWORD", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# ----- Telegram Bot -----
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ----- Functions -----
def send_whatsapp(phone, message):
    try:
        pywhatkit.sendwhatmsg_instantly(phone, message)
        print(f"WhatsApp sent to {phone}")
    except Exception as e:
        print(f"WhatsApp failed for {phone}: {e}")

def send_email(to_email, subject, message):
    try:
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            raise RuntimeError("Email credentials are not configured")
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email failed for {to_email}: {e}")

def send_telegram(username, message):
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("Telegram bot token is not configured")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": username, "text": message}
        requests.post(url, data=payload)
        print(f"Telegram sent to {username}")
    except Exception as e:
        print(f"Telegram failed for {username}: {e}")

def send_viber(phone, message):
    # Placeholder: Viber API integration needed
    print(f"Viber sent to {phone}: {message}")
