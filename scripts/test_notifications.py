"""
Test Notifications Script
- Simulates sending different types of notifications
- Logs results in Google Sheets (Notifications tab)
"""

import logging
from guzo_booking_bot.modules.notification_log import log_notification

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_test_notifications():
    guest_name = "Test Guest"
    email_contact = "test@example.com"
    phone_contact = "+251911111111"

    # Simulate Email Notification
    try:
        # Here you would normally call notify.send_email(...)
        log_notification(guest_name, email_contact, "Email", "SUCCESS", "Test email sent successfully.")
    except Exception as e:
        log_notification(guest_name, email_contact, "Email", "FAILED", str(e))

    # Simulate SMS Notification
    try:
        # Here you would normally call notify.send_sms(...)
        log_notification(guest_name, phone_contact, "SMS", "SUCCESS", "Test SMS sent successfully.")
    except Exception as e:
        log_notification(guest_name, phone_contact, "SMS", "FAILED", str(e))

    # Simulate WhatsApp Notification
    try:
        # Here you would normally call notify.send_whatsapp(...)
        log_notification(guest_name, phone_contact, "WhatsApp", "SUCCESS", "Test WhatsApp sent successfully.")
    except Exception as e:
        log_notification(guest_name, phone_contact, "WhatsApp", "FAILED", str(e))

    # Simulate Telegram Notification
    try:
        log_notification(guest_name, "5582570428", "Telegram", "SUCCESS", "Test Telegram message sent successfully.")
    except Exception as e:
        log_notification(guest_name, "5582570428", "Telegram", "FAILED", str(e))

    # Simulate Viber Notification
    try:
        log_notification(guest_name, phone_contact, "Viber", "SUCCESS", "Test Viber message sent successfully.")
    except Exception as e:
        log_notification(guest_name, phone_contact, "Viber", "FAILED", str(e))


if __name__ == "__main__":
    logging.info("Ã°ÂÂÂ Starting Notification Tests...")
    run_test_notifications()
    logging.info("Ã¢ÂÂ Notification tests completed.")
