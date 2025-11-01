# guzo_backend/modules/messaging.py
import pywhatkit
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Bot
from twilio.rest import Client
from guzo_backend import config

# ----------------------------
# WhatsApp via Twilio
# ----------------------------
def send_whatsapp_message(to_number, message):
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=config.TWILIO_PHONE,
        body=message,
        to=f"whatsapp:{to_number}"
    )
    print(f"WhatsApp sent to {to_number}")

# ----------------------------
# Email
# ----------------------------
def send_email_message(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = config.GMAIL_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.GMAIL_EMAIL, config.GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email failed for {to_email}: {e}")

# ----------------------------
# Telegram
# ----------------------------
def send_telegram_message(username, message):
    bot = Bot(token=config.TELEGRAM_TOKEN)
    bot.send_message(chat_id=username, text=message)
    print(f"Telegram sent to {username}")

# ----------------------------
# Viber (simple example)
# ----------------------------
def send_viber_message(number, message):
    # Use Twilio/Viber API
    print(f"Viber sent to {number}: \n{message}")
