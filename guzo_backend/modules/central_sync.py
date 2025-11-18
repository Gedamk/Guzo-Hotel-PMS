# -*- coding: utf-8 -*-
"""
central_sync.py – Guzo Central Booking Synchronization (v2.8)
--------------------------------------------------------------
Automatically syncs every confirmed hotel booking into the
Guzo Central System Google Sheet for unified dashboard reporting.
"""

import os
import datetime
import logging
from dotenv import load_dotenv
from guzo_backend.modules import google_sheets

env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

CENTRAL_DASHBOARD_ID = os.getenv("CENTRAL_DASHBOARD_SHEET_ID")
CENTRAL_DASHBOARD_NAME = os.getenv("CENTRAL_DASHBOARD_SHEET_NAME", "Guzo_Central_System")

def sync_booking_to_central(booking_data: dict):
    """Push one confirmed booking into the Central_Bookings tab."""
    try:
        if not CENTRAL_DASHBOARD_ID:
            raise ValueError("CENTRAL_DASHBOARD_SHEET_ID not found in .env")

        client = google_sheets.init_client()
        spreadsheet = client.open_by_key(CENTRAL_DASHBOARD_ID)

        try:
            ws = spreadsheet.worksheet("Central_Bookings")
        except Exception:
            ws = spreadsheet.add_worksheet(title="Central_Bookings", rows=1000, cols=20)
            ws.append_row([
                "Timestamp", "Hotel Name", "Guest Name", "Source", "Check-In Date",
                "Check-Out Date", "Nights", "Room Type", "Rate Per Night (ETB)",
                "Total Revenue (ETB)", "Payment Status", "Payment Method",
                "Confirmation ID", "Handled By", "Auto Reply", "Remark"
            ])

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now,
            booking_data.get("Hotel Name", ""),
            booking_data.get("Guest Name", ""),
            booking_data.get("Source", "Telegram"),
            booking_data.get("Check-In Date", ""),
            booking_data.get("Check-Out Date", ""),
            booking_data.get("Nights", ""),
            booking_data.get("Room Type", ""),
            booking_data.get("Rate Per Night (ETB)", ""),
            booking_data.get("Total Revenue (ETB)", ""),
            booking_data.get("Payment Status", ""),
            booking_data.get("Payment Method", ""),
            booking_data.get("Confirmation ID", ""),
            "System Bot",
            "Auto Synced via Guzo",
            "Central record from Telegram"
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        logging.info(f"[CentralSync] ✅ Booking synced for {booking_data.get('Hotel Name')}")
        return True
    except Exception as e:
        logging.error(f"[CentralSync] ❌ Sync failed: {e}")
        return False
# ============================================================
# SELF-TEST EXECUTION (Run manually for verification)
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🧪 Running standalone Central Sync test...")

    test_booking = {
        "Hotel Name": "Sofi Hotel",
        "Guest Name": "Test Guest",
        "Source": "ManualTest",
        "Check-In Date": "2025-11-07",
        "Check-Out Date": "2025-11-09",
        "Nights": 2,
        "Room Type": "Deluxe",
        "Rate Per Night (ETB)": 2200,
        "Total Revenue (ETB)": 4400,
        "Payment Status": "Paid",
        "Payment Method": "Card",
        "Confirmation ID": "TEST-" + datetime.datetime.now().strftime("%H%M%S"),
    }

    result = sync_booking_to_central(test_booking)
    if result:
        print("✅ Test booking successfully added to Central_Bookings.")
    else:
        print("❌ Failed to sync test booking. Check logs for details.")
