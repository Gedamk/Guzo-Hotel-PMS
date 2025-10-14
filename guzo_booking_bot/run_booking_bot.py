# -*- coding: utf-8 -*-
"""
Guzo Booking Bot - Main Automation Script
-----------------------------------------
Processes new guest bookings from Google Sheets and updates their status.
"""

import os
import logging
from datetime import datetime
from guzo_booking_bot.modules import google_sheets

# === Logging Setup ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging (UTF-8 safe)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "booking_bot.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"          # ✅ ensures clean log text
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)


# === Main Processing Function ===
def process_new_bookings():
    logging.info("🚀 Starting Guzo Booking Bot process...")

    try:
        # Fetch new bookings
        new_bookings = google_sheets.get_new_guest_bookings()
        logging.info(f"Found {len(new_bookings)} new booking(s).")

        if not new_bookings:
            logging.info("No new bookings to process. Exiting.")
            return

        # Fetch hotel contacts if needed
        hotel_contacts = google_sheets.get_hotel_contacts()
        hotel_contact_dict = {h["Hotel name"]: h for h in hotel_contacts}

        for booking in new_bookings:
            guest_name = booking.get("Guest Name")
            hotel_name = booking.get("Hotel name")

            logging.info(f"Processing booking for guest: {guest_name} at {hotel_name}")

            try:
                # Example: Integrate notification/email sending here
                contact = hotel_contact_dict.get(hotel_name)
                if contact:
                    logging.info(f"Hotel contact found: {contact.get('email')}")

                # Mark booking as processed in Google Sheet
                google_sheets.update_booking_status(guest_name, status="Processed")
                logging.info(f"✅ Booking for {guest_name} processed successfully.")

            except Exception as e:
                logging.error(f"❌ Error processing booking for {guest_name}: {e}")

    except Exception as e:
        logging.error(f"Unexpected error during booking processing: {e}")

    logging.info("🏁 Booking Bot process completed successfully.")


# === Run the bot if this script is executed directly ===
if __name__ == "__main__":
    process_new_bookings()
