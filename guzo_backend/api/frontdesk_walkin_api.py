# guzo_backend/api/frontdesk_walkin_api.py

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-walkin"])


class WalkInBookingCreate(BaseModel):
    """
    Payload expected from the FrontDesk Walk-In form.
    This matches the fields we send from the React UI.
    """

    property_code: str = Field(..., description="Hotel property code, e.g. DRE001")
    room_type: Optional[str] = Field(None, description="Room type code/name")
    guest_name: str
    check_in: date
    check_out: date
    rate_per_night_etb: Optional[float] = None
    total_amount_etb: Optional[float] = None
    payment_method: Optional[str] = None
    amount_paid_now_etb: Optional[float] = None
    notes: Optional[str] = None

    @validator("check_out")
    def validate_dates(cls, v, values):
        check_in = values.get("check_in")
        if check_in and v < check_in:
            raise ValueError("check_out must be on or after check_in")
        return v


@router.post("/walkin", status_code=status.HTTP_201_CREATED)
def create_walkin_booking(payload: WalkInBookingCreate, db: Session = Depends(get_db)):
    """
    Create a new walk-in booking from the Front Desk console.

    For now we:
    - insert into `bookings` table with the core fields we already use in the UI
    - mark status = 'in_house' (guest is already at desk)
    - channel = 'WalkIn'
    """

    # Compute total if not provided
    nights = (payload.check_out - payload.check_in).days or 1
    total_amount = payload.total_amount_etb
    if total_amount is None and payload.rate_per_night_etb is not None:
        total_amount = payload.rate_per_night_etb * nights

    try:
        insert_sql = text(
            """
            INSERT INTO bookings (
                property_code,
                guest_name,
                room_type,
                check_in,
                check_out,
                status,
                channel,
                total_amount_etb,
                notes
            )
            VALUES (
                :property_code,
                :guest_name,
                :room_type,
                :check_in,
                :check_out,
                :status,
                :channel,
                :total_amount_etb,
                :notes
            )
            RETURNING id
            """
        )

        result = db.execute(
            insert_sql,
            {
                "property_code": payload.property_code,
                "guest_name": payload.guest_name,
                "room_type": payload.room_type,
                "check_in": payload.check_in,
                "check_out": payload.check_out,
                # guest is at the desk and checked in
                "status": "in_house",
                "channel": "WalkIn",
                "total_amount_etb": total_amount,
                "notes": payload.notes,
            },
        )
        new_id_row = result.fetchone()
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # This is what drives the "Failed to create walk-in booking" message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating walk-in booking: {exc}",
        ) from exc

    # Frontend only cares that it succeeded and will refresh via /frontdesk/bookings
    return {"ok": True, "booking_id": int(new_id_row[0]) if new_id_row else None}
