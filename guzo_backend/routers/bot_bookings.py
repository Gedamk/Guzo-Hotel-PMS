# guzo_backend/routers/bot_bookings.py
#
# FastAPI router for creating bookings from the Telegram bot / backend calls.
#
# ✅ Directly calls insert_booking_from_bot(...) in postgres_bookings
# ✅ Returns real booking_id from PostgreSQL
# ✅ Keeps response shape you already use on the frontend

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from guzo_backend.modules.postgres_bookings import insert_booking_from_bot

router = APIRouter(prefix="/bot", tags=["bot"])


# Map property_code -> hotel name for response / message
HOTEL_NAME_BY_PROPERTY = {
    "DRE001": "Dream Big  Hotel",   # keep double space to match your Sheets
    "NN002": "N&N Luxury Hotel",
}


class BotBookingRequest(BaseModel):
    property_code: str = Field(..., example="DRE001")
    check_in: str = Field(..., example="2025-11-25")   # 'YYYY-MM-DD'
    check_out: str = Field(..., example="2025-11-27")  # 'YYYY-MM-DD'
    guest_name: str = Field(..., example="Test Guest From Bot")
    channel: str = Field(..., example="Telegram Bot")
    total_amount_etb: float = Field(..., example=8000.0)
    currency: str = Field("ETB", example="ETB")
    room_type: Optional[str] = Field(None, example="Family Room")
    guest_email: Optional[str] = Field(None, example="guest@example.com")
    guest_count: Optional[int] = Field(None, example=2)
    payment_method: Optional[str] = Field(None, example="Card")
    payment_status: Optional[str] = Field(None, example="pending")
    guest_phone: Optional[str] = Field(None, example="+251911000000")
    adults: Optional[int] = Field(None, example=2)
    children: Optional[int] = Field(None, example=2)
    purpose_of_visit: Optional[str] = Field(None, example="Leisure")
    notes: Optional[str] = Field(None, example="Online reservation via Telegram")


class BotBookingResponse(BaseModel):
    booking_id: Optional[int]
    property_code: str
    hotel_name: str
    check_in: str
    check_out: str
    nights: int
    guest_name: str
    channel: str
    total_amount_etb: float
    currency: str
    status: str
    message: str


def _compute_nights(check_in: str, check_out: str) -> int:
    """
    Helper to compute nights from two 'YYYY-MM-DD' strings.
    """
    ci = datetime.strptime(check_in, "%Y-%m-%d").date()
    co = datetime.strptime(check_out, "%Y-%m-%d").date()
    return (co - ci).days


@router.post("/bookings", response_model=BotBookingResponse)
async def create_bot_booking(payload: BotBookingRequest) -> BotBookingResponse:
    """
    Create a booking from the bot/backend and save it into PostgreSQL.

    1) Validates dates and nights.
    2) Calls insert_booking_from_bot(...) which writes to the bookings table.
    3) Returns the new booking_id plus a human-friendly message.
    """
    # --- validate nights ----------------------------------------------------
    try:
        nights = _compute_nights(payload.check_in, payload.check_out)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {e}",
        )

    if nights <= 0:
        raise HTTPException(
            status_code=400,
            detail="check_out must be after check_in (nights must be positive).",
        )

    # --- hotel name for response -------------------------------------------
    hotel_name = HOTEL_NAME_BY_PROPERTY.get(
        payload.property_code,
        payload.property_code,  # fallback: just echo the code
    )

    # --- write into PostgreSQL ---------------------------------------------
    try:
        booking_id = insert_booking_from_bot(
            property_code=payload.property_code,
            check_in=payload.check_in,
            check_out=payload.check_out,
            guest_name=payload.guest_name,
            channel=payload.channel,
            total_amount_etb=payload.total_amount_etb,
            currency=payload.currency,
            room_type=payload.room_type,
            guest_email=payload.guest_email,
            payment_method=payload.payment_method,
            payment_status=payload.payment_status,
            guest_phone=payload.guest_phone,
            adults=payload.adults,
            children=payload.children,
            purpose_of_visit=payload.purpose_of_visit,
            notes=payload.notes,
        )
    except Exception as e:
        # Surface the real error so we can see what's wrong
        raise HTTPException(
            status_code=500,
            detail=f"DB error in insert_booking_from_bot: {e}",
        )

    if booking_id is None:
        status = "pending"
        message = (
            f"Booking *not* saved to database for {hotel_name} "
            f"({payload.property_code}) – please check server logs."
        )
    else:
        status = "confirmed"
        message = (
            f"Backend booking created for {hotel_name} "
            f"({payload.property_code}) – {nights} night(s), "
            f"{payload.total_amount_etb} {payload.currency}."
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
        total_amount_etb=payload.total_amount_etb,
        currency=payload.currency,
        status=status,
        message=message,
    )
