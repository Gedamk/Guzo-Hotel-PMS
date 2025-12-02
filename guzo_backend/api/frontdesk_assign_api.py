# guzo_backend/api/frontdesk_assign_api.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-assign"])


class AssignRoomPayload(BaseModel):
    booking_id: int
    property_code: Optional[str] = None
    room_number: str


@router.post("/assign-room", status_code=status.HTTP_200_OK)
def assign_room(payload: AssignRoomPayload, db: Session = Depends(get_db)):
    """
    Assign a physical room number to an existing booking.

    We keep it simple:
    - update `bookings.room_number`
    - set status to 'in_house'
    """

    try:
        update_sql = text(
            """
            UPDATE bookings
            SET
                room_number = :room_number,
                status      = 'in_house'
            WHERE id = :booking_id
            """
        )

        result = db.execute(
            update_sql,
            {
                "room_number": payload.room_number,
                "booking_id": payload.booking_id,
            },
        )
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found for assignment",
            )

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # This drives the "Failed to assign room" message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning room: {exc}",
        ) from exc

    # Frontend just refreshes /frontdesk/bookings after this
    return {"ok": True}
