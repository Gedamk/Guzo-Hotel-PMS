# guzo_backend/api/bookings_actions_api.py
#
# Room assignment actions for front office:
# - POST /bookings/{booking_id}/assign-room
# - POST /bookings/{booking_id}/clear-room
#
# Uses:
#   - bookings           (your main bookings table)
#   - room_assignments   (we just created this table)
#
# No references to non-existent columns like booking_code or room_number on bookings.

from __future__ import annotations

import os
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import require_pms_permission


# -----------------------------------------------------------------------------
# Simple connection helper (same pattern as availability_api)
# -----------------------------------------------------------------------------
def get_connection():
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


router = APIRouter(prefix="/bookings", tags=["bookings-actions"])


# -----------------------------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------------------------
class AssignRoomRequest(BaseModel):
    property_code: str
    room_number: str
    force: bool = False


class RoomAssignmentResult(BaseModel):
    booking_id: int
    room_number: Optional[str]
    force: bool = False
    conflict_booking_id: Optional[int] = None


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------
def fetch_booking(booking_id: int, property_code: str) -> Dict[str, Any]:
    """
    Load a booking row by id using only REAL columns that exist in `bookings`.
    """
    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    hotel_id,
                    confirmation_id,
                    guest_name,
                    check_in_date,
                    check_out_date,
                    room_type,
                    booking_status,
                    payment_status
                FROM bookings
                WHERE id = %s AND property_code = %s
                """,
                (booking_id, property_code),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Booking not found")
            return dict(row)
    except HTTPException:
        # re-raise cleanly
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL error in fetch_booking: {e}",
        )
    finally:
        conn.close()


def get_current_assignment(booking_id: int) -> Optional[str]:
    """
    Returns current room_number for this booking_id from room_assignments (if any).
    """
    try:
        conn = get_connection()
    except Exception:
        # if DB is totally down, higher-level code will hit that first
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT room_number
                FROM room_assignments
                WHERE booking_id = %s
                """,
                (booking_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def find_conflict_booking_id(
    *,
    hotel_id: int,
    room_number: str,
    check_in_date,
    check_out_date,
    exclude_booking_id: int,
) -> Optional[int]:
    """
    Check if the same room_number is already assigned to another overlapping
    booking for this hotel.
    """
    try:
        conn = get_connection()
    except Exception:
        # If DB is unavailable, let the main assign code surface connection error.
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ra.booking_id
                FROM room_assignments ra
                JOIN bookings b ON b.id = ra.booking_id
                WHERE
                    ra.room_number = %s
                    AND b.hotel_id = %s
                    AND b.check_in_date < %s     -- other booking starts before this ends
                    AND b.check_out_date > %s    -- and ends after this starts
                    AND ra.booking_id <> %s
                LIMIT 1
                """,
                (
                    room_number,
                    hotel_id,
                    check_out_date,
                    check_in_date,
                    exclude_booking_id,
                ),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("/{booking_id}/assign-room", response_model=RoomAssignmentResult)
def assign_room(
    booking_id: int,
    payload: AssignRoomRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Assign a physical room number to a booking.

    - If `force=false` (default), we check for conflicting assignments:
      same room, overlapping dates, same hotel.
    - If a conflict exists, returns HTTP 409 with conflict_booking_id.
    - If OK (or forced), upserts into room_assignments.
    """
    property_code = payload.property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="frontdesk.assign_room",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    booking = fetch_booking(booking_id, property_code)

    room_number = payload.room_number.strip()
    if not room_number:
        raise HTTPException(status_code=400, detail="room_number cannot be empty")

    # conflict check (unless forced)
    conflict_id = find_conflict_booking_id(
        hotel_id=booking["hotel_id"],
        room_number=room_number,
        check_in_date=booking["check_in_date"],
        check_out_date=booking["check_out_date"],
        exclude_booking_id=booking_id,
    )

    if conflict_id is not None and not payload.force:
        # report the conflict as a 409 (Conflict)
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Room is already assigned to another overlapping booking.",
                "conflict_booking_id": conflict_id,
            },
        )

    # perform the upsert into room_assignments
    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO room_assignments (booking_id, room_number)
                    VALUES (%s, %s)
                    ON CONFLICT (booking_id)
                    DO UPDATE SET
                        room_number = EXCLUDED.room_number,
                        assigned_at = now()
                    """,
                    (booking_id, room_number),
                )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL error in assign_room: {e}",
        )
    finally:
        conn.close()

    return RoomAssignmentResult(
        booking_id=booking_id,
        room_number=room_number,
        force=payload.force,
        conflict_booking_id=conflict_id if payload.force else None,
    )


@router.post("/{booking_id}/clear-room", response_model=RoomAssignmentResult)
def clear_room(
    booking_id: int,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Clear the assigned room for this booking (if any).
    """
    # Ensure the booking exists
    property_code = property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="frontdesk.assign_room",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    fetch_booking(booking_id, property_code)

    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    previous_room: Optional[str] = None

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM room_assignments ra
                    USING bookings b
                    WHERE ra.booking_id = %s
                      AND b.id = ra.booking_id
                      AND b.property_code = %s
                    RETURNING ra.room_number
                    """,
                    (booking_id, property_code),
                )
                row = cur.fetchone()
                if row:
                    previous_room = row[0]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQL error in clear_room: {e}",
        )
    finally:
        conn.close()

    return RoomAssignmentResult(
        booking_id=booking_id,
        room_number=None,
        force=False,
        conflict_booking_id=None,
    )
