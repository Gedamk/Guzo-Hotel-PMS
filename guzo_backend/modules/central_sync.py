# -*- coding: utf-8 -*-
"""
central_sync.py – Guzo Central Booking Synchronization (v3.1)
--------------------------------------------------------------
Sync every booking into:
• Google Sheets Central_Bookings tab (for dashboards)
• PostgreSQL `bookings` table (for analytics & reporting)

If no property_code is present, we still sync to Sheets,
but skip the Postgres insert to avoid hotel_id=NULL errors.
"""

import os
import datetime
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from guzo_backend.modules import google_sheets
from guzo_backend.modules import postgres_bookings

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Environment
# -------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

CENTRAL_DASHBOARD_ID = os.getenv("CENTRAL_DASHBOARD_SHEET_ID")
CENTRAL_DASHBOARD_NAME = os.getenv(
    "CENTRAL_DASHBOARD_SHEET_NAME", "Guzo_Central_System"
)


# -------------------------------------------------
# Small helper – support both sheet + normalized keys
# -------------------------------------------------
def _pick(d: Dict[str, Any], *keys, default: Any = "") -> Any:
    """
    Return the first non-empty value for the given keys from dict d.
    Example:
        _pick(booking, "Hotel Name", "hotel_name")
    """
    for k in keys:
        if k in d:
            v = d.get(k)
            if v not in (None, ""):
                return v
    return default


# -------------------------------------------------
# Core sync function
# -------------------------------------------------
def sync_booking_to_central(booking_data: Dict[str, Any]) -> bool:
    """
    Push one booking into:
      1) Google Sheets → Central_Bookings tab
      2) PostgreSQL → bookings table (via postgres_bookings)

    Returns True if at least one destination (Sheets or Postgres) succeeded.
    """
    sheets_ok = False
    pg_ok = False

    # Normalized, human-friendly values (used for sheet row + logs)
    hotel_name = _pick(booking_data, "Hotel Name", "hotel_name")
    guest_name = _pick(booking_data, "Guest Name", "guest_name")
    source = _pick(booking_data, "Source", "source", default="Telegram")
    check_in_date = _pick(
        booking_data,
        "Check-In Date",
        "Check In Date",
        "check_in_date",
    )
    check_out_date = _pick(
        booking_data,
        "Check-Out Date",
        "Check Out Date",
        "check_out_date",
    )
    nights = _pick(booking_data, "Nights", "nights")
    room_type = _pick(booking_data, "Room Type", "room_type")
    rate_per_night = _pick(
        booking_data,
        "Rate Per Night (ETB)",
        "rate_per_night_etb",
    )
    total_revenue = _pick(
        booking_data,
        "Total Revenue (ETB)",
        "total_revenue_etb",
    )
    payment_status = _pick(booking_data, "Payment Status", "payment_status")
    payment_method = _pick(booking_data, "Payment Method", "payment_method")
    confirmation_id = _pick(
        booking_data,
        "Confirmation ID",
        "confirmation_id",
    )
    property_code = _pick(
        booking_data,
        "property_code",
        "Property Code",
        default=None,
    )

    # ----------------------------------------
    # 1) Sync to Google Sheets
    # ----------------------------------------
    if not CENTRAL_DASHBOARD_ID:
        logger.warning(
            "[CentralSync] ⚠️ CENTRAL_DASHBOARD_SHEET_ID not set – skipping Google Sheets sync."
        )
    else:
        try:
            client = google_sheets.init_client()
            spreadsheet = client.open_by_key(CENTRAL_DASHBOARD_ID)

            try:
                ws = spreadsheet.worksheet("Central_Bookings")
            except Exception:
                # If the worksheet doesn't exist, create + add headers
                ws = spreadsheet.add_worksheet(
                    title="Central_Bookings",
                    rows=1000,
                    cols=20,
                )
                ws.append_row(
                    [
                        "Timestamp",
                        "Hotel Name",
                        "Guest Name",
                        "Source",
                        "Check-In Date",
                        "Check-Out Date",
                        "Nights",
                        "Room Type",
                        "Rate Per Night (ETB)",
                        "Total Revenue (ETB)",
                        "Payment Status",
                        "Payment Method",
                        "Confirmation ID",
                        "Handled By",
                        "Auto Reply",
                        "Remark",
                    ]
                )

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                now_str,
                hotel_name,
                guest_name,
                source,
                check_in_date,
                check_out_date,
                nights,
                room_type,
                rate_per_night,
                total_revenue,
                payment_status,
                payment_method,
                confirmation_id,
                "System Bot",
                "Auto Synced via Guzo",
                "Central record from Telegram",
            ]

            ws.append_row(row, value_input_option="USER_ENTERED")
            logger.info(
                "[CentralSync] ✅ Booking synced to Central_Bookings for hotel=%s, confirmation_id=%s",
                hotel_name,
                confirmation_id,
            )
            sheets_ok = True
        except Exception:
            logger.exception("[CentralSync] ❌ Google Sheets sync failed.")

    # ----------------------------------------
    # 2) Sync to PostgreSQL
    # ----------------------------------------
    if not property_code:
        logger.warning(
            "[CentralSync] ⚠️ No property_code in booking; skipping Postgres save "
            "(confirmation_id=%s)",
            confirmation_id,
        )
    else:
        try:
            # Make sure the booking dict we send has a normalized property_code key
            booking_for_pg = dict(booking_data)
            booking_for_pg["property_code"] = property_code

            pg_id = postgres_bookings.save_booking_to_postgres(booking_for_pg)
            logger.info(
                "[CentralSync] ✅ Saved booking to Postgres with id=%s (confirmation_id=%s)",
                pg_id,
                confirmation_id,
            )
            pg_ok = True
        except Exception:
            logger.exception(
                "[CentralSync] ⚠️ Failed to save booking to Postgres (confirmation_id=%s)",
                confirmation_id,
            )

    return sheets_ok or pg_ok


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

        # 👉 IMPORTANT for Postgres:
        # Replace "DRE001" with a REAL property_code from your `hotels` table.
        # Run in psql:
        #   SELECT id, property_code, name FROM hotels;
        "property_code": "DRE001",
        "guest_email": "test.guest@example.com",
    }

    result = sync_booking_to_central(test_booking)
    if result:
        print("✅ Test booking successfully synced (Sheets and/or Postgres).")
    else:
        print("❌ Failed to sync test booking. Check logs for details.")
