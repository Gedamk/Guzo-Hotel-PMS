# guzo_backend/modules/postgres_bookings.py
#
# Save Guzo bookings into PostgreSQL
#
# ✅ Single source of truth for booking inserts
# ✅ Works both for:
#      • Telegram bot (insert_booking_from_bot / save_booking_to_postgres)
#      • CentralSync from Google Sheets (insert_booking_from_sheet_dict)
# ✅ Fills hotel_id using property_code (FK to hotels table)
# ✅ Matches CURRENT bookings table schema:
#      id, confirmation_id, hotel_id, guest_name, guest_email,
#      check_in_date, check_out_date, nights,
#      room_type, rate_per_night_etb, total_revenue_etb,
#      payment_method, booking_status, payment_status,
#      source, payment_date, property_code, created_at
# ✅ UTF-8 safe, psycopg2-only, no global state

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = int(os.getenv("GUZO_DB_PORT", "5432"))

    if not password:
        raise RuntimeError("GUZO_DB_PASSWORD is not set in environment")

    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    return conn


# ---------------------------------------------------------------------------
# Helpers: hotels / foreign key resolution
# ---------------------------------------------------------------------------
def _get_hotel_row_by_property_code(
    property_code: str, conn
) -> Optional[Dict[str, Any]]:
    """
    Look up the hotel row (id, property_code) by property_code.

    NOTE: Your hotels table does NOT have a hotel_name column,
    so we only select id and property_code.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, property_code
            FROM hotels
            WHERE property_code = %s
            """,
            (property_code,),
        )
        return cur.fetchone()


# ---------------------------------------------------------------------------
# Core insert helper (MATCHES CURRENT BOOKINGS TABLE)
# ---------------------------------------------------------------------------
def _insert_booking_core(
    conn,
    *,
    hotel_id: int,
    property_code: str,
    check_in_date: str,   # 'YYYY-MM-DD'
    check_out_date: str,  # 'YYYY-MM-DD'
    nights: int,
    guest_name: str,
    guest_email: Optional[str],
    total_amount_etb: float,
    booking_status: str,
    payment_status: str,
    source: str,
    room_type: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> int:
    """
    Low-level insert into bookings table. Returns new booking id.

    Columns in DB:
      id, confirmation_id, hotel_id, guest_name, guest_email,
      check_in_date, check_out_date, nights,
      room_type, rate_per_night_etb, total_revenue_etb,
      payment_method, booking_status, payment_status,
      source, payment_date, property_code, created_at
    """

    # Derive rate_per_night_etb from total_amount_etb and nights
    nights_for_rate = nights if nights and nights > 0 else 1
    rate_per_night = float(total_amount_etb) / float(nights_for_rate)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO bookings (
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
                payment_status,
                source,
                property_code,
                created_at
            )
            VALUES (
                %s,           -- hotel_id
                %s,           -- guest_name
                %s,           -- guest_email
                %s::date,     -- check_in_date
                %s::date,     -- check_out_date
                %s,           -- nights
                %s,           -- room_type
                %s,           -- rate_per_night_etb
                %s,           -- total_revenue_etb
                %s,           -- payment_method
                %s,           -- booking_status
                %s,           -- payment_status
                %s,           -- source
                %s,           -- property_code
                NOW()         -- created_at
            )
            RETURNING id;
            """,
            (
                hotel_id,
                guest_name,
                guest_email,
                check_in_date,
                check_out_date,
                nights,
                room_type,
                rate_per_night,
                total_amount_etb,
                payment_method,
                booking_status,
                payment_status,
                source,
                property_code,
            ),
        )
        row = cur.fetchone()
        booking_id = row["id"]
        logger.info(
            "[PostgresBookings] ✅ Inserted booking id=%s for guest=%s property_code=%s",
            booking_id,
            guest_name,
            property_code,
        )
        return booking_id


# ---------------------------------------------------------------------------
# 1) Insert from Google Sheets row (CentralSync)
# ---------------------------------------------------------------------------
def insert_booking_from_sheet_dict(row: Dict[str, Any]) -> Optional[int]:
    """
    Insert a booking coming from a Google Sheets row.

    Expected keys in `row` (Hotel_Contacts_Master / Central_Bookings style):
      - 'Property Code'
      - 'Hotel Name'
      - 'Check-In Date'
      - 'Check-Out Date'
      - 'Nights'
      - 'Total Revenue (ETB)'
      - 'Guest Name'
      - 'Guest Email'
      - 'Source'
      - 'Channel'
      - 'Booking Status'
      - 'Payment Status'
      - 'Rooms'
      - 'Currency'
      - 'Payment Date' (optional)
    """
    required_keys: List[str] = [
        "Property Code",
        "Guest Name",
        "Guest Email",
        "Check-In Date",
        "Check-Out Date",
        "Total Revenue (ETB)",
        "Channel",
        "Booking Status",
        "Payment Status",
        "Rooms",
        "Currency",
    ]

    missing = [k for k in required_keys if not row.get(k)]
    if missing:
        logger.warning(
            "[PostgresBookings] SKIP booking from sheet – missing required fields %s in row: %s",
            missing,
            row,
        )
        return None

    property_code = str(row["Property Code"]).strip()
    guest_name = str(row["Guest Name"]).strip()
    guest_email = str(row["Guest Email"]).strip()
    check_in = str(row["Check-In Date"]).strip()
    check_out = str(row["Check-Out Date"]).strip()
    channel = str(row["Channel"]).strip()
    booking_status = str(row["Booking Status"]).strip() or "Confirmed"
    payment_status = str(row["Payment Status"]).strip() or "Unpaid"
    currency = str(row["Currency"]).strip() or "ETB"  # currently not stored in DB

    # Nights: prefer numeric column if present, else compute
    nights_val = row.get("Nights")
    try:
        nights = int(nights_val) if nights_val is not None else None
    except Exception:
        nights = None

    from datetime import datetime

    if nights is None:
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()
        nights = (co - ci).days

    try:
        total_amount_etb = float(row["Total Revenue (ETB)"])
    except Exception:
        total_amount_etb = 0.0

    try:
        rooms = int(row["Rooms"])
    except Exception:
        rooms = 1

    source = str(row.get("Source", channel or "Google Sheet")).strip() or "Google Sheet"

    # Optional: derive a very rough room_type / payment_method for now
    room_type = None  # could be updated later when you have that column in Sheets
    payment_method = None

    conn = get_connection()
    try:
        with conn:
            hotel = _get_hotel_row_by_property_code(property_code, conn)
            if not hotel:
                logger.warning(
                    "[PostgresBookings] SKIP – no hotel found for property_code=%s row=%s",
                    property_code,
                    row,
                )
                return None

            hotel_id = hotel["id"]

            booking_id = _insert_booking_core(
                conn,
                hotel_id=hotel_id,
                property_code=property_code,
                check_in_date=check_in,
                check_out_date=check_out,
                nights=nights,
                guest_name=guest_name,
                guest_email=guest_email,
                total_amount_etb=total_amount_etb,
                booking_status=booking_status,
                payment_status=payment_status,
                source=source,
                room_type=room_type,
                payment_method=payment_method,
            )
            return booking_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2) Insert from Telegram Bot (used by FastAPI /bot/bookings endpoint)
# ---------------------------------------------------------------------------
def insert_booking_from_bot(
    *,
    property_code: str,
    check_in: str,      # 'YYYY-MM-DD'
    check_out: str,     # 'YYYY-MM-DD'
    guest_name: str,
    channel: str,
    total_amount_etb: float,
    currency: str = "ETB",
) -> Optional[int]:
    """
    Insert a booking created by Telegram bot and return new booking id.
    Guest email is optional / handled at Sheets level, so not required here.
    """
    from datetime import datetime

    ci = datetime.strptime(check_in, "%Y-%m-%d").date()
    co = datetime.strptime(check_out, "%Y-%m-%d").date()
    nights = (co - ci).days
    if nights <= 0:
        logger.error(
            "[PostgresBookings] ❌ Bot booking has non-positive nights (check_in=%s, check_out=%s)",
            check_in,
            check_out,
        )
        return None

    conn = get_connection()
    try:
        with conn:
            hotel = _get_hotel_row_by_property_code(property_code, conn)
            if not hotel:
                logger.error(
                    "[PostgresBookings] ❌ Bot booking – no hotel found for property_code=%s",
                    property_code,
                )
                return None

            hotel_id = hotel["id"]

            # For now: no room_type / payment_method / guest_email at DB layer
            room_type = None
            payment_method = None
            booking_status = "confirmed"
            payment_status = "paid"  # change to 'unpaid' if you prefer
            source = channel or "Telegram Bot"

            booking_id = _insert_booking_core(
                conn,
                hotel_id=hotel_id,
                property_code=property_code,
                check_in_date=check_in,
                check_out_date=check_out,
                nights=nights,
                guest_name=guest_name,
                guest_email=None,
                total_amount_etb=float(total_amount_etb),
                booking_status=booking_status,
                payment_status=payment_status,
                source=source,
                room_type=room_type,
                payment_method=payment_method,
            )
            return booking_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3) Backwards-compatible wrapper for legacy bot code
# ---------------------------------------------------------------------------
def save_booking_to_postgres(booking: Dict[str, Any]) -> Optional[int]:
    """
    Backwards-compatible entry point used by the Telegram bot / legacy code.

    This accepts either:
      • A "sheet style" dict (keys like 'Property Code', 'Check-In Date', ...)
      • A "bot style" dict (keys like 'property_code', 'check_in', 'check_out', ...)

    It routes to the appropriate insert function and returns the new booking id,
    or None if the payload is invalid.
    """

    # Case 1: looks like a Google Sheets row
    if "Property Code" in booking or "Check-In Date" in booking:
        logger.debug("[PostgresBookings] save_booking_to_postgres() detected sheet-style payload")
        return insert_booking_from_sheet_dict(booking)

    # Case 2: looks like a bot payload
    if "property_code" in booking and "check_in" in booking and "check_out" in booking:
        logger.debug("[PostgresBookings] save_booking_to_postgres() detected bot-style payload")

        property_code = str(booking["property_code"]).strip()
        check_in = str(booking["check_in"]).strip()
        check_out = str(booking["check_out"]).strip()

        guest_name = str(
            booking.get("guest_name")
            or booking.get("guest")
            or "Guest"
        ).strip()

        channel = str(
            booking.get("channel", "Telegram Bot")
        ).strip() or "Telegram Bot"

        total_amount_etb_raw = (
            booking.get("total_amount_etb")
            or booking.get("total_amount")
            or 0.0
        )
        try:
            total_amount_etb = float(total_amount_etb_raw)
        except Exception:
            total_amount_etb = 0.0

        currency = str(
            booking.get("currency", "ETB")
        ).strip() or "ETB"

        return insert_booking_from_bot(
            property_code=property_code,
            check_in=check_in,
            check_out=check_out,
            guest_name=guest_name,
            channel=channel,
            total_amount_etb=total_amount_etb,
            currency=currency,
        )

    # Unknown payload shape
    logger.error(
        "[PostgresBookings] ❌ save_booking_to_postgres() received unsupported payload keys: %s",
        list(booking.keys()),
    )
    return None
