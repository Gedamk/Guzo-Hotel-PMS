# -*- coding: utf-8 -*-
"""
postgres_bookings.py – Save Guzo bookings into PostgreSQL

This version is designed to work with your current `bookings` table
and booking flow, without needing any ALTER TABLE / superuser access.

It assumes:

- A `bookings` table with (at least) these columns:

    confirmation_id
    hotel_id
    guest_name
    guest_email
    check_in_date
    check_out_date
    nights
    room_type
    rate_per_night_etb
    total_revenue_etb
    payment_method
    booking_status
    payment_status

- A `hotels` table with:

    id
    property_code   (unique per hotel)

- Optionally, a UNIQUE or PRIMARY KEY constraint on `confirmation_id`
  in `bookings` so that ON CONFLICT (confirmation_id) works.
"""

import os
import logging
from typing import Dict, Any

import psycopg2

logger = logging.getLogger(__name__)


# ----------------------------------------
# Connection helper
# ----------------------------------------
def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        raise RuntimeError("GUZO_DB_PASSWORD is not set in environment")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


def _pick(d: Dict[str, Any], *keys):
    """
    Helper: return the first non-empty value found in `d` for the given keys.
    Works with both normalized keys and raw Google Sheet headers.
    """
    for k in keys:
        if k in d:
            v = d.get(k)
            if v not in (None, ""):
                return v
    return None


# ----------------------------------------
# Core insert function used by the bot
# ----------------------------------------
def insert_booking_from_sheet_dict(booking: Dict[str, Any]) -> int:
    """
    Insert a booking coming from the Google Sheets / bot flow.

    Google Sheet headers:

        "Timestamp"
        "Guest Name"
        "Source"
        "Check-In Date"
        "Check-Out Date"
        "Nights"
        "Room Type"
        "Rate Per Night (ETB)"
        "Total Revenue (ETB)"
        "Booking Status"
        "Confirmation ID"
        "Payment Status"
        "Payment Date"
        "Payment Method"
        "Handled By"
        "Auto Reply"
        "Remark"

    We also expect EXTRA FIELDS from the bot flow (not in the sheet):

        property_code   (e.g., "DRE001") – used to resolve hotel_id
        guest_email     – email collected by the bot

    This version only writes to the columns that actually
    exist in your current `bookings` table.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO bookings (
                        confirmation_id,
                        hotel_id,
                        guest_name,
                        guest_email,
                        check_in_date,
                        check_out_date,
                        nights,
                        room_type,
                        rate_per_night_etb,
                        total_revenue_etb,
                        payment_method,
                        booking_status,
                        payment_status
                    )
                    VALUES (
                        %(confirmation_id)s,
                        (SELECT id FROM hotels WHERE property_code = %(property_code)s),
                        %(guest_name)s,
                        %(guest_email)s,
                        %(check_in_date)s,
                        %(check_out_date)s,
                        %(nights)s,
                        %(room_type)s,
                        %(rate_per_night_etb)s,
                        %(total_revenue_etb)s,
                        %(payment_method)s,
                        %(booking_status)s,
                        %(payment_status)s
                    )
                    ON CONFLICT (confirmation_id)
                    DO UPDATE SET
                        hotel_id = EXCLUDED.hotel_id,
                        guest_name = EXCLUDED.guest_name,
                        guest_email = EXCLUDED.guest_email,
                        check_in_date = EXCLUDED.check_in_date,
                        check_out_date = EXCLUDED.check_out_date,
                        nights = EXCLUDED.nights,
                        room_type = EXCLUDED.room_type,
                        rate_per_night_etb = EXCLUDED.rate_per_night_etb,
                        total_revenue_etb = EXCLUDED.total_revenue_etb,
                        payment_method = EXCLUDED.payment_method,
                        booking_status = EXCLUDED.booking_status,
                        payment_status = EXCLUDED.payment_status
                    RETURNING id;
                """

                # Map from sheet headers + normalized keys into DB params
                params = {
                    "confirmation_id": _pick(
                        booking,
                        "confirmation_id",
                        "Confirmation ID",
                    ),
                    "property_code": _pick(
                        booking,
                        "property_code",
                        "Property Code",
                    ),

                    "guest_name": _pick(
                        booking,
                        "guest_name",
                        "Guest Name",
                    ),
                    "guest_email": _pick(
                        booking,
                        "guest_email",
                        "Guest Email",
                    ),

                    "check_in_date": _pick(
                        booking,
                        "check_in_date",
                        "Check-In Date",
                        "Check In Date",
                    ),
                    "check_out_date": _pick(
                        booking,
                        "check_out_date",
                        "Check-Out Date",
                        "Check Out Date",
                    ),
                    "nights": _pick(
                        booking,
                        "nights",
                        "Nights",
                    ),
                    "room_type": _pick(
                        booking,
                        "room_type",
                        "Room Type",
                    ),

                    "rate_per_night_etb": _pick(
                        booking,
                        "rate_per_night_etb",
                        "Rate Per Night (ETB)",
                    ),
                    "total_revenue_etb": _pick(
                        booking,
                        "total_revenue_etb",
                        "Total Revenue (ETB)",
                    ),

                    "payment_method": _pick(
                        booking,
                        "payment_method",
                        "Payment Method",
                    ),
                    "booking_status": _pick(
                        booking,
                        "booking_status",
                        "Booking Status",
                    ),
                    "payment_status": _pick(
                        booking,
                        "payment_status",
                        "Payment Status",
                    ),
                }

                logger.info("[PostgresBookings] Inserting booking: %s", params)

                cur.execute(sql, params)
                row = cur.fetchone()
                new_id = row[0] if row else None

                logger.info(
                    "[PostgresBookings] ✅ Saved booking %s to Postgres with id=%s",
                    params.get("confirmation_id"),
                    new_id,
                )
                return new_id
    finally:
        conn.close()


# ----------------------------------------
# Backwards-compatible wrapper
# ----------------------------------------
def save_booking_to_postgres(booking: Dict[str, Any]) -> int:
    """
    Old name kept for compatibility with existing code
    (e.g. message_router / booking_flow).

    Simply forwards to insert_booking_from_sheet_dict().
    """
    return insert_booking_from_sheet_dict(booking)


if __name__ == "__main__":
    # Optional manual test (you can run: python -m guzo_backend.modules.postgres_bookings)
    from datetime import date

    sample = {
        "confirmation_id": "TEST-123",
        "property_code": "TEST_HOTEL",
        "guest_name": "Test Guest",
        "guest_email": "test@example.com",
        "check_in_date": date.today(),
        "check_out_date": date.today(),
        "nights": 1,
        "room_type": "Test Room",
        "rate_per_night_etb": 1000,
        "total_revenue_etb": 1000,
        "payment_method": "Cash",
        "booking_status": "Confirmed",
        "payment_status": "Pending",
    }

    print("Inserting test booking...")
    bid = save_booking_to_postgres(sample)
    print("Inserted booking id:", bid)
