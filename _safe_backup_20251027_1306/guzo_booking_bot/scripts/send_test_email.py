# scripts/send_test_email.py
"""
Test script to send an email using the configured provider (SMTP or SendGrid).
"""

import logging
from guzo_booking_bot import config
from guzo_booking_bot.modules import notifications

def main():
    logging.basicConfig(level=logging.INFO)

    to_email = input("Enter a test recipient email: ").strip()
    subject = "Guzo Booking Bot - Test Email"
    message = "Hello! ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ This is a test email from your Guzo Booking Bot setup."

    try:
        notifications.send_email(to_email, subject, message)
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Test email sent to {to_email}")
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to send email: {e}")

if __name__ == "__main__":
    main()
