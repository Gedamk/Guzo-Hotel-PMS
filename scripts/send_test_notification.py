# scripts/send_test_notification.py
import os
import sys
from dotenv import load_dotenv

# Load environment
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from guzo_booking_bot.modules import notifications

def main():
    print("=== Guzo Notification Test ===")
    print(f"Environment: {os.getenv('ENV', 'development')}")
    print(f"Primary Email: {os.getenv('GMAIL_EMAIL')}")

    # Ask recipient
    recipient_email = input("Enter test recipient EMAIL: ").strip()
    recipient_sms = input("Enter test recipient SMS number (+countrycode...): ").strip()
    recipient_telegram = input("Enter Telegram chat_id (or leave blank): ").strip()
    recipient_viber = input("Enter Viber user_id (or leave blank): ").strip()

    subject = "Test Notification - Guzo Guest Assist"
    body = "✅ This is a test notification from your Guzo booking assistant system."

    # --- Email ---
    try:
        notifications.send_email(recipient_email, subject, body)
        print(f"📧 Email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

    # --- SMS ---
    try:
        if recipient_sms:
            notifications.send_sms(recipient_sms, body)
            print(f"📱 SMS sent to {recipient_sms}")
    except Exception as e:
        print(f"❌ SMS failed: {e}")

    # --- WhatsApp ---
    try:
        if recipient_sms:
            notifications.send_whatsapp(recipient_sms, body)
            print(f"💬 WhatsApp sent to {recipient_sms}")
    except Exception as e:
        print(f"❌ WhatsApp failed: {e}")

    # --- Telegram ---
    try:
        if recipient_telegram:
            notifications.send_telegram(recipient_telegram, body)
            print(f"🤖 Telegram sent to {recipient_telegram}")
    except Exception as e:
        print(f"❌ Telegram failed: {e}")

    # --- Viber ---
    try:
        if recipient_viber:
            notifications.send_viber(recipient_viber, body)
            print(f"📲 Viber sent to {recipient_viber}")
    except Exception as e:
        print(f"❌ Viber failed: {e}")

if __name__ == "__main__":
    sys.exit(main())
