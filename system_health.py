# -*- coding: utf-8 -*-
"""
System Health Monitor
Runs checks across Google Sheets, Email, Telegram, Payments, and Retry Handler.
Logs results and notifies managers via Email + Telegram.
"""

import logging
from guzo_booking_bot.modules import (
    google_sheets,
    email_sender,
    telegram_sender,
    payments,
    retry_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/health_check.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SystemHealth")


def check_google_sheets():
    try:
        google_sheets.get_guest_assist()
        logger.info("Google Sheets connection OK")
        return "OK"
    except Exception as e:
        logger.error(f"Google Sheets FAILED: {e}")
        return "FAILED"


def check_email():
    try:
        email_sender.send_notification(
            "manager@guzoassist.com",
            "[TEST] Email Service Check",
            "This is a test email from Guzo system health monitor."
        )
        logger.info("Email service OK")
        return "OK"
    except Exception as e:
        logger.error(f"Email FAILED: {e}")
        return "FAILED"


def check_telegram():
    try:
        telegram_sender.send_message("✅ Telegram service check successful.")
        logger.info("Telegram service OK")
        return "OK"
    except Exception as e:
        logger.error(f"Telegram FAILED: {e}")
        return "FAILED"


def check_payments():
    try:
        payments.create_payment_intent(
            booking={"Guest Name": "HealthCheck"},
            amount=100,  # $1 test
            currency="usd",
            description="HealthCheck Test"
        )
        logger.info("Payments service OK (Stripe)")
        return "OK"
    except Exception as e:
        logger.error(f"Payments FAILED: {e}")
        return "FAILED"


def check_retry_handler():
    try:
        retry_handler.retry_failed_notifications()
        logger.info("Retry handler executed")
        return "OK"
    except Exception as e:
        logger.error(f"Retry Handler FAILED: {e}")
        return "FAILED"


def run_health_check():
    logger.info("=======================================")
    logger.info("Running System Health Check...")
    logger.info("=======================================")

    results = {
        "Google Sheets": check_google_sheets(),
        "Email": check_email(),
        "Telegram": check_telegram(),
        "Payments": check_payments(),
        "Retry Handler": check_retry_handler(),
    }

    # Summary
    report = "📋 System Health Summary:\n\n"
    for k, v in results.items():
        status = "✅ OK" if v == "OK" else "❌ FAILED"
        report += f"{k}: {status}\n"

    logger.info("=======================================")
    logger.info("Health Check Summary:")
    for k, v in results.items():
        logger.info(f"{k}: {v}")
    logger.info("=======================================")

    # ✅ Send report to managers
    email_sender.send_notification("manager@guzoassist.com", "System Health Report", report)
    telegram_sender.send_message(report)

    logger.info("Health check finished.")


if __name__ == "__main__":
    run_health_check()
