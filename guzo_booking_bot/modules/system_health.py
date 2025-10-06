# -*- coding: utf-8 -*-
"""
System Health Checker
Runs diagnostic tests for all major Guzo Guest Assist modules
and prints a summary report.
"""

import os
import sys
import logging
from datetime import datetime

from guzo_booking_bot.modules import (
    google_sheets,
    email_sender,
    telegram_sender,
    payments,
    retry_handler,
)

# ============================
# Logger Setup
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SystemHealth")

def check_env():
    """Check critical environment variables"""
    required = [
        "STRIPE_SECRET_KEY",
        "SENDGRID_API_KEY",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error(f"❌ Missing environment vars: {', '.join(missing)}")
        return False
    logger.info("✅ Environment variables OK")
    return True

def check_google_sheets():
    """Check if Sheets client works"""
    try:
        client = google_sheets.init_client()
        if client:
            logger.info("✅ Google Sheets connection OK")
            return True
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
    return False

def check_email():
    """Send a test email"""
    try:
        status = email_sender.send_email(
            "manager@guzoassist.com",
            "System Health Check",
            f"🟢 Test email sent at {datetime.now()}"
        )
        if status:
            logger.info("✅ Email service OK")
            return True
    except Exception as e:
        logger.error(f"❌ Email service error: {e}")
    return False

def check_telegram():
    """Send a test Telegram message"""
    try:
        resp = telegram_sender.send_message(
            f"🟢 Test message sent at {datetime.now()}"
        )
        if resp:
            logger.info("✅ Telegram service OK")
            return True
    except Exception as e:
        logger.error(f"❌ Telegram service error: {e}")
    return False

def check_payments():
    """Create a test Stripe payment intent"""
    try:
        intent = payments.create_payment_intent(
            booking={"Guest Name": "HealthCheck"},
            amount=100,  # $1
            currency="usd"
        )
        if intent:
            logger.info("✅ Payments service OK (Stripe)")
            return True
    except Exception as e:
        logger.error(f"❌ Payment service error: {e}")
    return False

def check_retries():
    """Check retry handler"""
    try:
        retry_handler.retry_failed_notifications()
        logger.info("✅ Retry handler executed")
        return True
    except Exception as e:
        logger.error(f"❌ Retry handler error: {e}")
    return False

def main():
    logger.info("=======================================")
    logger.info("🩺 Running System Health Check...")
    logger.info("=======================================")

    checks = {
        "Environment": check_env(),
        "Google Sheets": check_google_sheets(),
        "Email": check_email(),
        "Telegram": check_telegram(),
        "Payments": check_payments(),
        "Retry Handler": check_retries(),
    }

    logger.info("=======================================")
    logger.info("📊 Health Check Summary:")
    for service, ok in checks.items():
        status = "✅ OK" if ok else "❌ FAIL"
        logger.info(f"{service}: {status}")

    logger.info("=======================================")
    logger.info("🏁 Health check finished.")

if __name__ == "__main__":
    main()
