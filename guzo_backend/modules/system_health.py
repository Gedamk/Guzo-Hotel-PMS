# -*- coding: utf-8 -*-
"""
system_health.py – Guzo Guest Assist System Health Checker (v3.1)
-----------------------------------------------------------------
Runs diagnostic tests across all major modules and prints a summary.
Fully UTF-8 clean and compatible with the backend + Streamlit dashboards.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# ✅ Import project modules
from guzo_backend.modules import (
    google_sheets,
    email_sender,
    telegram_notifier,
    payments,
    retry_handler,
)

# ======================================================
# 🧩 Environment Setup
# ======================================================
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

# ======================================================
# 🪵 Logger Configuration
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SystemHealth")


# ======================================================
# 🔍 Health Check Functions
# ======================================================
def check_env():
    """Verify that all required environment variables are present."""
    required_vars = [
        "STRIPE_SECRET_KEY",
        "SENDGRID_API_KEY",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"⚠️ Missing environment variables: {', '.join(missing)}")
        return False
    logger.info("✅ Environment variables OK")
    return True


def check_google_sheets():
    """Check Google Sheets client connectivity."""
    try:
        client = google_sheets.init_client()
        if client:
            logger.info("✅ Google Sheets connection OK")
            return True
        else:
            raise RuntimeError("Google Sheets client not initialized")
    except Exception as e:
        logger.error(f"❌ Google Sheets error: {e}")
        return False


def check_email():
    """Check SendGrid email sending."""
    try:
        status = email_sender.send_invoice_email(
            to_email=os.getenv("TO_EMAIL", "manager@guzoassist.com"),
            subject="✅ Guzo System Health Check",
            body_text=f"<strong>Test email sent successfully at {datetime.now()}</strong>"
        )
        if status:
            logger.info("✅ Email service OK")
            return True
        else:
            raise RuntimeError("Email not sent successfully")
    except Exception as e:
        logger.error(f"❌ Email service error: {e}")
        return False


def check_telegram():
    """Check Telegram bot connectivity."""
    try:
        test_message = f"✅ System health test message sent at {datetime.now()}"
        result = telegram_notifier.send_telegram_message(test_message)
        if result:
            logger.info("✅ Telegram service OK")
            return True
        else:
            raise RuntimeError("Telegram message not sent")
    except Exception as e:
        logger.error(f"❌ Telegram service error: {e}")
        return False


def check_payments():
    """Check Stripe payments service."""
    try:
        test_intent = payments.create_payment_intent(
            booking={"Guest Name": "HealthCheck"},
            amount=100,  # $1 test charge
            currency="usd",
        )
        if test_intent:
            logger.info("✅ Stripe payments service OK")
            return True
        else:
            raise RuntimeError("Stripe test intent not created")
    except Exception as e:
        logger.error(f"❌ Payment service error: {e}")
        return False


def check_retries():
    """Check retry handler for failed notifications."""
    try:
        retry_handler.retry_failed_notifications()
        logger.info("✅ Retry handler executed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Retry handler error: {e}")
        return False


# ======================================================
# 🧭 Main Health Summary
# ======================================================
def main():
    logger.info("=======================================")
    logger.info("🚀 Running Guzo Guest Assist System Health Check...")
    logger.info("=======================================")

    checks = {
        "Environment": check_env(),
        "Google Sheets": check_google_sheets(),
        "Email (SendGrid)": check_email(),
        "Telegram Bot": check_telegram(),
        "Payments (Stripe)": check_payments(),
        "Retry Handler": check_retries(),
    }

    logger.info("=======================================")
    logger.info("🩺 Health Check Summary:")
    for service, ok in checks.items():
        status = "✅ OK" if ok else "❌ FAIL"
        logger.info(f"{service}: {status}")

    logger.info("=======================================")
    overall_status = "✅ ALL SYSTEMS OPERATIONAL" if all(checks.values()) else "⚠️ SOME CHECKS FAILED"
    logger.info(overall_status)
    logger.info("🏁 Health check completed.")


# ======================================================
# 🚀 Run as Script
# ======================================================
if __name__ == "__main__":
    main()
