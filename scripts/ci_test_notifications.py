"""
CI/CD Notification Test Module
- Automatically test Email, SMS, WhatsApp, Telegram, and Viber notifications
- Designed for integration with GitHub Actions, GitLab CI, or local pre-deploy checks
"""

from guzo_booking_bot.modules import notifications as notify
from guzo_booking_bot import config as cfg
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Use environment variable for test recipient override
TEST_EMAIL = os.getenv("TEST_EMAIL", "gedam_ka@yahoo.com")
TEST_PHONE = os.getenv("TEST_PHONE", "+251900000000")  # default placeholder
TEST_TELEGRAM_ID = int(os.getenv("TEST_TELEGRAM_ID", "123456789"))

# Sample booking data for notifications
test_booking = {
    "Hotel Name": "Guzo Hotel",
    "Guest Name": "John Doe",
    "Check-in": "2025-10-28",
    "Check-out": "2025-10-30",
    "Room": "101",
    "Source": "Booking.com",
    "Contact": TEST_PHONE,
    "TelegramChatID": TEST_TELEGRAM_ID,
    "Status": "Confirmed"
}

message = (
    f"Test Booking Notification!\n"
    f"Hotel: {test_booking['Hotel Name']}\n"
    f"Guest: {test_booking['Guest Name']}\n"
    f"Check-in: {test_booking['Check-in']}\n"
    f"Check-out: {test_booking['Check-out']}\n"
    f"Room: {test_booking['Room']}\n"
    f"Source: {test_booking['Source']}\n"
    f"Status: {test_booking['Status']}"
)

def test_email():
    try:
        notify.send_email(to_email=TEST_EMAIL, subject="CI/CD Test Email", body=message)
        logger.info("✅ Email test sent successfully")
    except Exception as e:
        logger.error(f"❌ Email test failed: {e}")

def test_sms():
    try:
        notify.send_sms(to_phone=TEST_PHONE, message=message)
        logger.info("✅ SMS test sent successfully")
    except Exception as e:
        logger.error(f"❌ SMS test failed: {e}")

def test_whatsapp():
    try:
        notify.send_whatsapp(to_phone=TEST_PHONE, message=message)
        logger.info("✅ WhatsApp test sent successfully")
    except Exception as e:
        logger.error(f"❌ WhatsApp test failed: {e}")

def test_telegram():
    if cfg.TELEGRAM_TOKEN:
        try:
            notify.send_telegram(chat_id=TEST_TELEGRAM_ID, message=message)
            logger.info("✅ Telegram test sent successfully")
        except Exception as e:
            logger.error(f"❌ Telegram test failed: {e}")

def test_viber():
    if cfg.VIBER_API_KEY:
        try:
            notify.send_viber(to_phone=TEST_PHONE, message=message)
            logger.info("✅ Viber test sent successfully")
        except Exception as e:
            logger.error(f"❌ Viber test failed: {e}")

def run_all_tests():
    logger.info("🔹 Running all notification tests...")
    test_email()
    test_sms()
    test_whatsapp()
    test_telegram()
    test_viber()
    logger.info("🔹 All notification tests completed")

if __name__ == "__main__":
    run_all_tests()
