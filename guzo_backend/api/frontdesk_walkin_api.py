# guzo_backend/api/frontdesk_walkin_api.py

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-walkin"])


class WalkInBookingCreate(BaseModel):
    """
    Payload expected from the Front Desk Walk-In form.
    This should line up with what the React WalkInBookingModal sends.
    """

    property_code: str = Field(..., description="Hotel property code, e.g. DRE001")
    room_number: Optional[str] = Field(
        None,
        description="Assigned room number (e.g. 200). If omitted, stays as TBD.",
    )
    room_type: Optional[str] = Field(
        None,
        description="Room type code/name (optional – for future use).",
    )
    guest_name: str
    check_in_date: date
    check_out_date: date
    rate_per_night_etb: Optional[float] = None
    total_amount_etb: Optional[float] = None
    payment_method: Optional[str] = None
    amount_paid_now_etb: Optional[float] = None
    notes: Optional[str] = None

    @validator("check_out_date")
    def validate_dates(cls, v, values):
        check_in = values.get("check_in_date")
        if check_in and v < check_in:
            raise ValueError("check_out_date must be on or after check_in_date")
        return v


def _generate_confirmation_id(property_code: str) -> str:
    """
    Simple confirmation ID generator for walk-ins.
    Example: GZ-WI-DRE001-251202094530
    """
    ts = datetime.now().strftime("%y%m%d%H%M%S")
    return f"GZ-WI-{property_code}-{ts}"


@router.post("/walkin", status_code=status.HTTP_201_CREATED)
def create_walkin_booking(
    payload: WalkInBookingCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new walk-in booking from the Front Desk console.

    Design:
    - Insert into `bookings` table using the same core fields
      that the Front Desk and Housekeeping flows expect:
        * confirmation_id
        * guest_name
        * property_code
        * room_number (optional)
        * check_in_date
        * check_out_date
        * booking_status
        * channel
        * total_amount
        * notes

    - For now we treat walk-ins as already at the desk and checked in:
        booking_status = 'Checked In'
        channel        = 'Walk-In'

    - The Front Desk UI will refresh via /frontdesk/bookings after success.
    """

    # Compute nights & total if not explicitly provided
    nights = (payload.check_out_date - payload.check_in_date).days or 1
    total_amount = payload.total_amount_etb
    if total_amount is None and payload.rate_per_night_etb is not None:
        total_amount = payload.rate_per_night_etb * nights

    confirmation_id = _generate_confirmation_id(payload.property_code)

    try:
        insert_sql = text(
            """
            INSERT INTO bookings (
                confirmation_id,
                guest_name,
                property_code,
                room_number,
                check_in_date,
                check_out_date,
                booking_status,
                channel,
                total_amount,
                notes
            )
            VALUES (
                :confirmation_id,
                :guest_name,
                :property_code,
                :room_number,
                :check_in_date,
                :check_out_date,
                :booking_status,
                :channel,
                :total_amount,
                :notes
            )
            RETURNING id
            """
        )

        result = db.execute(
            insert_sql,
            {
                "confirmation_id": confirmation_id,
                "guest_name": payload.guest_name,
                "property_code": payload.property_code,
                "room_number": payload.room_number,
                "check_in_date": payload.check_in_date,
                "check_out_date": payload.check_out_date,
                # Guest is created as in-house for walk-in
                "booking_status": "Checked In",
                "channel": "Walk-In",
                "total_amount": total_amount,
                "notes": payload.notes,
            },
        )
        new_id_row = result.fetchone()
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # Drives the "Failed to create walk-in booking" error message in the UI
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating walk-in booking: {exc}",
        ) from exc

    # Frontend only needs to know it succeeded; it will re-fetch bookings.
    return {"ok": True, "booking_id": int(new_id_row[0]) if new_id_row else None}
