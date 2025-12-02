# guzo_backend/api/frontdesk_assign_room_api.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from guzo_backend.dependencies import get_db  # <-- we use the shared DB dependency


router = APIRouter(
    prefix="/frontdesk",
    tags=["frontdesk-assign-room"],
)


class AssignRoomPayload(BaseModel):
    booking_id: int
    room_number: str


class BookingResponse(BaseModel):
    id: int
    guest_name: str
    check_in_date: str  # ISO date
    check_out_date: str  # ISO date
    booking_status: str
    property_code: str
    room_number: str


@router.post("/assign-room", response_model=BookingResponse, status_code=status.HTTP_200_OK)
def assign_room(payload: AssignRoomPayload, db: Session = Depends(get_db)) -> BookingResponse:
    """
    Assign a room number to a booking and mark it as in_house.

    This updates the bookings table:
      - room_number = :room_number
      - booking_status = 'in_house'

    Then returns the updated booking row for the front desk UI.
    """
    try:
        stmt = text(
            """
            UPDATE bookings
            SET
                room_number    = :room_number,
                booking_status = 'in_house'
            WHERE id = :booking_id
            RETURNING
                id,
                guest_name,
                check_in_date,
                check_out_date,
                booking_status,
                property_code,
                room_number
            """
        )

        result = db.execute(
            stmt,
            {
                "room_number": payload.room_number,
                "booking_id": payload.booking_id,
            },
        )

        row = result.fetchone()

        if row is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking {payload.booking_id} not found",
            )

        db.commit()

        # SQLAlchemy Row supports attribute-style access with the column names
        return BookingResponse(
            id=row.id,
            guest_name=row.guest_name,
            check_in_date=row.check_in_date.isoformat(),
            check_out_date=row.check_out_date.isoformat(),
            booking_status=row.booking_status,
            property_code=row.property_code,
            room_number=row.room_number,
        )

    except HTTPException:
        # already built a proper error response
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning room: {e}",
        )
