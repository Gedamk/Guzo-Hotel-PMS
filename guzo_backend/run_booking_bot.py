# -*- coding: utf-8 -*-
"""
run_booking_bot.py – Guzo Guest Assist (v10.2)
------------------------------------------------
Clean, UTF-8 safe version.
Automates test booking + confirmation using Google Sheets + SendGrid.
"""

import asyncio
import logging
from guzo_backend.modules import google_sheets
from guzo_backend.modules import auto_confirmation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def process_new_requests():
    """Simulate one booking and trigger confirmation."""
    logger.info("Starting Guzo Booking Bot process...")

    try:
        google_sheets.init_client()
        logger.info("Google Sheets client initialized successfully.")

        # Simulate one test booking
        guest = "Test Guest"
        hotel = "Sky Light Hotel"
        message = "Need booking for 2 nights"
        email = "manager@skylighthotel.com"

        google_sheets.log_new_request(guest, hotel, message)
        logger.info("Logged new request for test guest.")

        # ✅ Corrected call — no update/context args
        auto_confirmation.confirm_guest_request(
            guest_name=guest,
            hotel_name=hotel,
            message=message,
            recipient_email=email
        )

        logger.info("Booking confirmation process finished successfully.")

    except Exception as e:
        logger.error(f"Unexpected error during booking processing: {e}")

    logger.info("Booking Bot process completed successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(process_new_requests())
    except KeyboardInterrupt:
        logger.warning("Bot stopped manually by user.")
