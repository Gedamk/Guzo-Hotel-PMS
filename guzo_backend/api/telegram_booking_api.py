# guzo_backend/api/telegram_booking_api.py

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import record_pms_audit_log

router = APIRouter(
    prefix="/integrations/telegram",
    tags=["integrations-telegram"],
)


def normalize_property_code(raw: str) -> str:
    """
    Simple helper so we keep property codes consistent, e.g.
    'dre001' -> 'DRE001'.
    """
    if not raw:
        return raw
    return raw.strip().upper()


def _get_hotel_id(db: Session, property_code: str) -> int:
    row = db.execute(
        text(
            """
            SELECT id
            FROM hotels
            WHERE property_code = :property_code
            LIMIT 1
            """
        ),
        {"property_code": property_code},
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hotel found for property_code={property_code}",
        )

    return int(row[0])


class TelegramBookingCreate(BaseModel):
    """
    Payload expected from Telegram bot integration.
    This is what your Telegram bot (or curl) sends.
    """

    property_code: str = Field(..., description="Hotel property code, e.g. DRE001")
    guest_name: str
    check_in_date: date
    check_out_date: date
    room_type: Optional[str] = None
    room_number: Optional[str] = None
    total_amount_etb: Optional[float] = None
    notes: Optional[str] = None

    @validator("check_out_date")
    def validate_dates(cls, v, values):
        ci = values.get("check_in_date")
        if ci and v <= ci:
            raise ValueError("check_out_date must be after check_in_date")
        return v


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
def create_booking_from_telegram(
    payload: TelegramBookingCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new booking in the `bookings` table from Telegram integration.

    - Maps to your simplified `bookings` table schema:
        id SERIAL PRIMARY KEY,
        confirmation_id VARCHAR(50) UNIQUE NOT NULL,
        guest_name VARCHAR(100) NOT NULL,
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
        booking_status VARCHAR(30) NOT NULL,
        property_code VARCHAR(20) NOT NULL,
        room_number VARCHAR(10),
        room_type VARCHAR(50),
        total_amount_etb NUMERIC(12,2),
        channel VARCHAR(30),
        notes TEXT,
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now()
    """

    property_code = normalize_property_code(payload.property_code)

    # Generate a simple confirmation ID if you don't send one from Telegram
    # Example: GZ-TG-20251202-142355
    confirmation_id = f"GZ-TG-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    hotel_id = _get_hotel_id(db, property_code)

    # Basic default status/channel for Telegram bookings
    booking_status = "confirmed"
    channel = "Telegram"

    try:
        insert_sql = text(
            """
            INSERT INTO bookings (
                confirmation_id,
                hotel_id,
                guest_name,
                check_in_date,
                check_out_date,
                booking_status,
                property_code,
                room_number,
                room_type,
                total_amount_etb,
                channel,
                notes
            )
            VALUES (
                :confirmation_id,
                :hotel_id,
                :guest_name,
                :check_in_date,
                :check_out_date,
                :booking_status,
                :property_code,
                :room_number,
                :room_type,
                :total_amount_etb,
                :channel,
                :notes
            )
            RETURNING id
            """
        )

        result = db.execute(
            insert_sql,
            {
                "confirmation_id": confirmation_id,
                "hotel_id": hotel_id,
                "guest_name": payload.guest_name.strip(),
                "check_in_date": payload.check_in_date,
                "check_out_date": payload.check_out_date,
                "booking_status": booking_status,
                "property_code": property_code,
                "room_number": payload.room_number,
                "room_type": payload.room_type,
                "total_amount_etb": payload.total_amount_etb,
                "channel": channel,
                # mark these as Telegram-origin bookings for easy filtering
                "notes": f"[TG] {payload.notes or ''}".strip(),
            },
        )
        new_id_row = result.fetchone()
        booking_id = int(new_id_row[0]) if new_id_row else None
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email="telegram.bot@guzo.local",
            module="reservations",
            action="telegram_booking_created",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "confirmation_id": confirmation_id,
                "guest_name": payload.guest_name.strip(),
                "check_in_date": payload.check_in_date.isoformat(),
                "check_out_date": payload.check_out_date.isoformat(),
                "room_type": payload.room_type,
                "total_amount_etb": payload.total_amount_etb,
                "channel": channel,
            },
        )
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating Telegram booking: {exc}",
        ) from exc

    return {
        "ok": True,
        "booking_id": booking_id,
        "confirmation_id": confirmation_id,
    }
