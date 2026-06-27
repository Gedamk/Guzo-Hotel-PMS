# guzo_backend/api/frontdesk_assign_api.py

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..services.pms_security_service import record_pms_audit_log, require_pms_permission

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-assign"])


class AssignRoomPayload(BaseModel):
    booking_id: int
    property_code: Optional[str] = None
    room_number: str


@router.post("/assign-room", status_code=status.HTTP_200_OK)
def assign_room(
    payload: AssignRoomPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Assign a physical room number to an existing booking.

    We keep it simple:
    - update `bookings.room_number`
    - keep booking status unchanged until the check-in endpoint runs
    """

    property_code = payload.property_code.strip().upper() if payload.property_code else None
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.room_move",
        property_code=property_code,
        user_email=x_pms_user_email,
    )

    try:
        update_sql = text(
            """
            UPDATE bookings
            SET
                room_number = :room_number
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
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="frontdesk",
            action="room_assigned",
            record_type="booking",
            record_id=payload.booking_id,
            new_value={"room_number": payload.room_number},
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
