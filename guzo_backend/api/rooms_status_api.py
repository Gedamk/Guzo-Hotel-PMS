# guzo_backend/api/rooms_status_api.py
#
# Simple Ethiopian-style rooms grid for Front Office / Housekeeping.
# - GET /rooms/status-list?property_code=DRE001&business_date=YYYY-MM-DD
#   -> list all rooms for that property, with current guest (if any).
# - POST /rooms/status/update
#   -> update room.status (clean / dirty / ooo).

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guzo_backend.core.postgres_bookings import get_connection
from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import require_pms_permission, require_property_access

router = APIRouter(prefix="/rooms", tags=["rooms-status"])


class RoomStatusItem(BaseModel):
    property_code: str
    room_number: str
    room_type: Optional[str] = None
    floor: Optional[int] = None
    status: str  # 'clean', 'dirty', 'ooo'
    # current guest info (if occupied)
    current_booking_id: Optional[int] = None
    current_guest_name: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None


class RoomStatusUpdate(BaseModel):
    property_code: str
    room_number: str
    status: str  # 'clean', 'dirty', 'ooo'


@router.get("/status-list", response_model=List[RoomStatusItem])
def list_room_status(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: Optional[str] = Query(
        None, description="Business date YYYY-MM-DD, defaults to today"
    ),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Return all rooms for the property, with:
    - basic room info
    - today's in-house booking (if any) via room_assignments + bookings.
    """

    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    if business_date is None:
        biz = date.today()
    else:
        try:
            biz = date.fromisoformat(business_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid business_date format")

    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        with conn.cursor() as cur:
            # rooms LEFT JOIN room_assignments + bookings overlapping the date
            cur.execute(
                """
                SELECT
                    r.property_code,
                    r.room_number,
                    r.room_type,
                    r.floor,
                    r.status,
                    b.id           AS current_booking_id,
                    b.guest_name   AS current_guest_name,
                    b.check_in_date AS check_in,
                    b.check_out_date AS check_out
                FROM rooms r
                LEFT JOIN room_assignments ra
                    ON ra.room_number = r.room_number
                LEFT JOIN bookings b
                    ON b.id = ra.booking_id
                   AND b.check_in_date <= %(biz)s
                   AND b.check_out_date > %(biz)s
                WHERE r.property_code = %(pc)s
                ORDER BY r.room_number
                """,
                {"pc": property_code, "biz": biz},
            )
            rows = cur.fetchall()

        result: List[RoomStatusItem] = []
        for row in rows:
            (
                pc,
                room_number,
                room_type,
                floor,
                status,
                current_booking_id,
                current_guest_name,
                check_in,
                check_out,
            ) = row

            result.append(
                RoomStatusItem(
                    property_code=pc,
                    room_number=room_number,
                    room_type=room_type,
                    floor=floor,
                    status=status,
                    current_booking_id=current_booking_id,
                    current_guest_name=current_guest_name,
                    check_in=check_in,
                    check_out=check_out,
                )
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL error in rooms status: {e}")
    finally:
        conn.close()


@router.post("/status/update")
def update_room_status(
    payload: RoomStatusUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Update the housekeeping status of a room.

    Typical Ethiopian mid-scale codes:
    - 'clean'  -> ready to sell
    - 'dirty'  -> needs cleaning
    - 'ooo'    -> out of order
    """

    property_code = payload.property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="housekeeping.room_status_override",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    status_norm = payload.status.strip().lower()
    if status_norm not in ("clean", "dirty", "ooo"):
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Use one of: clean, dirty, ooo",
        )

    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rooms
                SET status = %s
                WHERE property_code = %s
                  AND room_number = %s
                """,
                (status_norm, property_code, payload.room_number),
            )
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Room not found for given property_code and room_number",
                )
        conn.commit()
        return {"ok": True, "status": status_norm}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"SQL error updating room status: {e}")
    finally:
        conn.close()
