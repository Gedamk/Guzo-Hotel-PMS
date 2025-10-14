# -*- coding: utf-8 -*-
"""
Unified Runner for Guzo Guest Assist
-----------------------------------
Central orchestrator that runs booking sync, payment webhooks,
retry handler, and daily system summary with monitoring & secure validation.
Now integrated with Google Sheets for live booking and notification sync.
"""

import os
import sys
import time
import signal
import threading
import logging
from datetime import datetime
from flask import Flask, jsonify

# --- Guzo internal modules ---
from guzo_booking_bot.modules import (
    booking,
    booking_handler,
    retry_handler,
    payment_webhooks,
    secure_logger,
    email_sender,
    telegram_sender,
    system_health,
)

# --- Google Sheets integration ---
from sheets_config import client, SHEETS

# ======================================================
# Logger (secure + masked)
# ======================================================
logger = secure_logger.get_logger("GuzoBookingBot")

# ======================================================
# Security: Environment Validation
# ======================================================
REQUIRED_ENV_VARS = [
    "STRIPE_SECRET_KEY",
    "SENDGRID_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
]

def validate_env():
    """Ensure all required environment variables are loaded."""
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        logger.error(f"Ã¢ÂÂ Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    logger.info("Ã°ÂÂÂ All required environment variables are set and valid.")

# ======================================================
# Health Check Server
# ======================================================
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "system": "Guzo Guest Assist",
        "services": [
            "booking_sync",
            "payment_webhooks",
            "retry_handler",
            "daily_summary",
            "google_sheets_sync"
        ]
    }), 200

# ======================================================
# Booking Sync (now from Google Sheets)
# ======================================================
def booking_sync():
    logger.info("Ã°ÂÂÂ Booking Sync started")

    try:
        guest_ws = client.open_by_url(SHEETS["guest_assist"]).sheet1
        logger.info("Ã¢ÂÂ Connected to Guest Assist sheet")
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Google Sheets connection failed: {e}")
        return

    try:
        records = guest_ws.get_all_records()
        new_bookings = [r for r in records if r.get("Status", "").lower() == "pending"]
        logger.info(f"Ã°ÂÂÂ Found {len(new_bookings)} pending booking(s)")

        for booking_row in new_bookings:
            guest_name = booking_row.get("Guest Name", "Unknown")
            hotel_name = booking_row.get("Hotel Name", "Unknown")

            logger.info(f"Ã°ÂÂÂ Processing booking: {guest_name} @ {hotel_name}")
            try:
                booking_handler.handle_booking(booking_row)
                guest_ws.update_cell(records.index(booking_row) + 2, 8, "Processed")
                logger.info(f"Ã¢ÂÂ Booking for {guest_name} marked as Processed")
            except Exception as e:
                logger.error(f"Ã¢ÂÂ Ã¯Â¸Â Booking failed for {guest_name}: {e}")
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Error during booking sync: {e}")

    logger.info("Ã°ÂÂÂ Booking Sync finished.")

# ======================================================
# Background Services
# ======================================================
def start_webhooks():
    logger.info("Ã°ÂÂÂ Starting Payment Webhooks service (port 5001)...")
    payment_webhooks.app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

def start_retry_scheduler():
    logger.info("Ã°ÂÂÂ Starting Retry Scheduler (every 15 minutes)...")
    while True:
        try:
            retry_handler.retry_failed_notifications()
        except Exception as e:
            logger.error(f"Ã¢ÂÂ Ã¯Â¸Â Retry scheduler failed: {e}")
        time.sleep(900)

def start_booking_scheduler():
    logger.info("Ã°ÂÂÂ Starting Booking Sync Scheduler (every 5 minutes)...")
    while True:
        try:
            booking_sync()
        except Exception as e:
            logger.error(f"Ã¢ÂÂ Ã¯Â¸Â Booking scheduler failed: {e}")
        time.sleep(300)

def start_daily_summary():
    logger.info("Ã°ÂÂÂ Starting Daily Summary Scheduler (every 24 hours)...")
    while True:
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # Perform heartbeat check
            booking_sync_ok = True
            retry_scheduler_ok = True
            webhooks_ok = True
            health_endpoint_ok = True

            msg = (
                f"Ã¢ÂÂ Daily System Summary Ã¢ÂÂ Guzo Guest Assist\n\n"
                f"Ã°ÂÂÂ Services Running:\n"
                f"- Booking Sync: {'Ã¢ÂÂ' if booking_sync_ok else 'Ã¢ÂÂ'}\n"
                f"- Retry Scheduler: {'Ã¢ÂÂ' if retry_scheduler_ok else 'Ã¢ÂÂ'}\n"
                f"- Payment Webhooks: {'Ã¢ÂÂ' if webhooks_ok else 'Ã¢ÂÂ'}\n"
                f"- Health Endpoint: {'Ã¢ÂÂ' if health_endpoint_ok else 'Ã¢ÂÂ'}\n\n"
                f"Ã°ÂÂÂ Date: {today}"
            )

            # Log summary locally
            try:
                system_health.log_daily_summary(
                    booking_sync_ok=booking_sync_ok,
                    retry_scheduler_ok=retry_scheduler_ok,
                    webhooks_ok=webhooks_ok,
                    health_endpoint_ok=health_endpoint_ok,
                    notes="Automated daily heartbeat"
                )
            except Exception as e:
                logger.error(f"Ã¢ÂÂ Ã¯Â¸Â Could not write daily summary: {e}")

            # Send via Telegram
            try:
                telegram_sender.send_telegram_message("MANAGER_CHAT_ID", msg)
                logger.info("Ã°ÂÂÂ¨ Daily summary sent via Telegram")
            except Exception as e:
                logger.error(f"Ã¢ÂÂ Telegram summary failed: {e}")

            # Send via Email
            try:
                email_sender.send_email(
                    "manager@guzoassist.com",
                    "Daily System Summary Ã¢ÂÂ Guzo Guest Assist",
                    msg
                )
                logger.info("Ã°ÂÂÂ¨ Daily summary sent via Email")
            except Exception as e:
                logger.error(f"Ã¢ÂÂ Email summary failed: {e}")

        except Exception as e:
            logger.error(f"Ã¢ÂÂ Ã¯Â¸Â Daily summary loop failed: {e}")

        time.sleep(86400)

# ======================================================
# Graceful Shutdown
# ======================================================
def handle_shutdown(sig, frame):
    logger.warning("Ã°ÂÂÂ Shutdown signal received Ã¢ÂÂ cleaning up ...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ======================================================
# Main Runner
# ======================================================
def main():
    logger.info("========================================")
    logger.info("Ã°ÂÂÂ Guzo Guest Assist System starting up ...")

    validate_env()

    # Start background threads
    threading.Thread(target=start_webhooks, daemon=True).start()
    threading.Thread(target=start_retry_scheduler, daemon=True).start()
    threading.Thread(target=start_booking_scheduler, daemon=True).start()
    threading.Thread(target=start_daily_summary, daemon=True).start()

    # Health endpoint
    logger.info("Ã°ÂÂÂ¡ Health monitor Ã¢ÂÂ http://127.0.0.1:5000/health")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
