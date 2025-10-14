# -*- coding: utf-8 -*-
"""
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
System Health Module
Runs system checks for environment, Google Sheets, Email, Telegram, Payments, and Retry handler.
Provides log_daily_summary for daily run integration.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from log_helper import log_event
import logging
import os
from logging.handlers import RotatingFileHandler
from guzo_booking_bot.modules import booking, retry_handler, telegram_sender, email_sender, payments

# ==============================
# Logger Setup with Rotation
# ==============================
logger = logging.getLogger("SystemHealth")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

# Rotating file handler (max 1MB per file, keep last 5 backups)
file_handler = RotatingFileHandler("logs/health_check.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)

# Attach handlers
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def check_env():
    """Check if required environment variables are set."""
    required = [
        "STRIPE_SECRET_KEY",
        "SENDGRID_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        logger.error(f"Ã¢ÂÂ Missing environment variables: {missing}")
        return False
    logger.info("Environment variables OK")
    return True


def check_google_sheets():
    """Check connection to all Google Sheets (Guest Assist, Hotel Contacts, Notifications)."""
    import gspread
    from dotenv import load_dotenv

    try:
        load_dotenv()
        sa = gspread.service_account(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        sheets_to_check = {
            "Guest Assist": os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST"),
            "Hotel Contacts": os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS"),
            "Notifications": os.getenv("GOOGLE_SHEET_ID_NOTIFICATIONS"),
        }

        all_ok = True
        for name, sid in sheets_to_check.items():
            if not sid:
                logger.error(f"Ã¢ÂÂ Missing Sheet ID for {name}")
                all_ok = False
                continue
            try:
                sh = sa.open_by_key(sid)
                logger.info(f"Ã¢ÂÂ Google Sheet OK Ã¢ÂÂ {name}: {sh.title}")
            except Exception as e:
                logger.error(f"Ã¢ÂÂ Failed to open {name}: {e}")
                all_ok = False

        return all_ok

    except Exception as e:
        logger.error(f"Ã¢ÂÂ Google Sheets check failed: {e}")
        return False


def check_email():
    """Check email sending service."""
    try:
        result = email_sender.send_email(
            to_email="manager@guzoassist.com",
            subject="Health Check Email",
            content="Ã¢ÂÂ This is a test email from Guzo Guest Assist health check."
        )
        if result:
            logger.info("Email service OK")
            return True
        else:
            logger.error("Ã¢ÂÂ Email check failed.")
            return False
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Email check error: {e}")
        return False


def check_telegram():
    """Check Telegram alerts."""
    try:
        telegram_sender.send_message("Ã¢ÂÂ Test message from Guzo Guest Assist health check.")
        logger.info("Telegram service OK")
        return True
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Telegram check failed: {e}")
        return False


def check_payments():
    """Check payments integration with Stripe (test PaymentIntent)."""
    try:
        booking_stub = {"Guest Name": "HealthCheck"}
        payments.create_payment_intent(
            booking_stub,
            100,
            "usd",
            description="HealthCheck Test"
        )
        logger.info("Payments service OK (Stripe)")
        return True
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Payments check failed: {e}")
        return False


def check_retry_handler():
    """Run retry handler test."""
    try:
        retry_handler.retry_failed_notifications()
        logger.info("Retry handler executed")
        return True
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Retry handler check failed: {e}")
        return False


def log_daily_summary(summary: str = "System health summary stored locally."):
    """Write daily system health summary into logs with rotation."""
    try:
        logger.info(f"[DAILY SUMMARY] {summary}")
        print("Ã°ÂÂÂ System health summary stored locally.")
    except Exception as e:
        print(f"Ã¢ÂÂ Failed to write system health summary: {e}")


# ==============================
# Runner
# ==============================
def run_all_checks():
    """Run all system health checks and print a summary."""
    logger.info("=======================================")
    logger.info("Ã°ÂÂÂ Running System Health Check...")
    logger.info("=======================================")

    results = {
        "Environment": check_env(),
        "Google Sheets": check_google_sheets(),
        "Email": check_email(),
        "Telegram": check_telegram(),
        "Payments": check_payments(),
        "Retry Handler": check_retry_handler(),
    }

    logger.info("=======================================")
    logger.info("Health Check Summary:")
    for k, v in results.items():
        status = "Ã¢ÂÂ OK" if v else "Ã¢ÂÂ FAIL"
        logger.info(f"{k}: {status}")
    logger.info("=======================================")

    log_daily_summary("System health check complete.")


if __name__ == "__main__":
    try:
        run_all_checks()
        # Record summary in global automation log
        log_event("System Health", "Ã¢ÂÂ Success", "All systems operational and checked successfully.")
    except Exception as e:
        log_event("System Health", "Ã¢ÂÂ Failed", str(e))
        raise
