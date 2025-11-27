# guzo_backend/routers/bot.py
#
# Endpoints used by Telegram / WhatsApp / etc. bots:
#   - GET  /bot/availability
#   - POST /bot/bookings
#
# These are called from guzo_booking_bot.main_telegram_bot.

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from guzo_backend.modules.postgres_bookings import (
    get_connection,
    insert_booking_from_bot,
)

router = APIRouter(prefix="/bot", tags=["bot"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class AvailabilityResponse(BaseModel):
    property_code: str
    check_in: str
    check_out: str
    requested_rooms: int
    total_rooms: int
    overlapping_bookings: int
    available_rooms: int
    available: bool
    message: str


class BotBookingRequest(BaseModel):
    property_code: str
    check_in: str   # 'YYYY-MM-DD'
    check_out: str  # 'YYYY-MM-DD'
    guest_name: str
    channel: str
    total_amount_etb: float


class BotBookingResponse(BaseModel):
    booking_id: int
    property_code: str
    hotel_name: Optional[str]
    check_in: str
    check_out: str
    nights: int
    guest_name: str
    channel: str
    total_amount_etb: float
    currency: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# GET /bot/availability
# ---------------------------------------------------------------------------
@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    check_in: str = Query(..., description="Check-in date 'YYYY-MM-DD'"),
    check_out: str = Query(..., description="Check-out date 'YYYY-MM-DD'"),
    rooms: int = Query(1, description="Number of rooms requested"),
):
    """
    Simple availability checker used by the bot.
    Counts total active rooms for the property and overlapping bookings.
    """
    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if co <= ci:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Total rooms for this property (rooms table)
                cur.execute(
                    """
                    SELECT COUNT(*) AS total_rooms
                    FROM rooms
                    WHERE property_code = %s
                      AND (is_active IS NULL OR is_active = TRUE)
                    """,
                    (property_code,),
                )
                row = cur.fetchone()
                total_rooms = row["total_rooms"] if row and row["total_rooms"] is not None else 0

                # 2) Overlapping bookings for this property
                # Overlap condition:
                #    NOT (existing.check_out_date <= requested_check_in
                #         OR existing.check_in_date >= requested_check_out)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(rooms), 0) AS overlapping_rooms
                    FROM bookings
                    WHERE property_code = %s
                      AND booking_status IN ('confirmed', 'in_house')
                      AND NOT (
                            check_out_date <= %s::date
                        OR  check_in_date  >= %s::date
                      )
                    """,
                    (property_code, check_in, check_out),
                )
                row = cur.fetchone()
                overlapping = row["overlapping_rooms"] if row and row["overlapping_rooms"] is not None else 0

                available_rooms = max(total_rooms - overlapping, 0)
                available = available_rooms >= rooms

                message = (
                    f"Yes, {available_rooms} room(s) available at {property_code} "
                    f"from {check_in} to {check_out}."
                    if available
                    else (
                        f"Sorry, only {available_rooms} room(s) available at {property_code} "
                        f"from {check_in} to {check_out}."
                    )
                )

                return AvailabilityResponse(
                    property_code=property_code,
                    check_in=check_in,
                    check_out=check_out,
                    requested_rooms=rooms,
                    total_rooms=total_rooms,
                    overlapping_bookings=overlapping,
                    available_rooms=available_rooms,
                    available=available,
                    message=message,
                )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /bot/bookings
# ---------------------------------------------------------------------------
@router.post("/bookings", response_model=BotBookingResponse)
def create_bot_booking(payload: BotBookingRequest):
    """
    Create a booking from Telegram bot.

    The bot already:
      - checks availability
      - collects guest_name, dates, total_amount_etb, channel

    Here we:
      - validate dates
      - insert into Postgres (bookings table)
      - return booking_id + summary back to the bot
    """
    try:
        ci = datetime.strptime(payload.check_in, "%Y-%m-%d").date()
        co = datetime.strptime(payload.check_out, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    nights = (co - ci).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    booking_id = insert_booking_from_bot(
        property_code=payload.property_code,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guest_name=payload.guest_name,
        channel=payload.channel,
        total_amount_etb=payload.total_amount_etb,
        currency="ETB",
    )

    if booking_id is None:
        raise HTTPException(status_code=500, detail="Failed to create booking in DB")

    # Optional: look up hotel_name from hotels table for nicer UX
    hotel_name: Optional[str] = None
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT hotel_name
                    FROM hotels
                    WHERE property_code = %s
                    """,
                    (payload.property_code,),
                )
                row = cur.fetchone()
                if row:
                    hotel_name = row["hotel_name"]
    finally:
        conn.close()

    message = (
        f"Backend booking created for {hotel_name or payload.property_code} "
        f"({payload.property_code}) – {nights} night(s), {payload.total_amount_etb} ETB."
    )

    return BotBookingResponse(
        booking_id=booking_id,
        property_code=payload.property_code,
        hotel_name=hotel_name,
        check_in=payload.check_in,
        check_out=payload.check_out,
        nights=nights,
        guest_name=payload.guest_name,
        channel=payload.channel,
        total_amount_etb=float(payload.total_amount_etb),
        currency="ETB",
        status="confirmed",
        message=message,
    )
