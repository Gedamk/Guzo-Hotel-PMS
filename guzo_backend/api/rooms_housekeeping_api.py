# guzo_backend/api/rooms_housekeeping_api.py
#
# Housekeeping view for Ethiopian mid-scale hotels:
# - GET  /housekeeping/rooms      → list rooms + FO/HK status for a given date
# - POST /housekeeping/update     → update housekeeping status of a room
#
# Uses the same Postgres connection helper as other APIs.

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from guzo_backend.core.postgres_db import get_connection  # <-- same helper as others


router = APIRouter(
    prefix="/housekeeping",
    tags=["housekeeping"],
)


# -------------------------------------------------------------------
# Pydantic models
# -------------------------------------------------------------------


class HousekeepingRoom(BaseModel):
    property_code: str
    room_number: str
    room_type: Optional[str] = None
    floor: Optional[int] = None

    # FO view of the room (what rooms/status API already uses)
    fo_status: str

    # HK status (for now we keep in the same "status" column)
    hk_status: str

    current_booking_id: Optional[int] = None
    current_guest_name: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None

    # Simple front-office flags for the board
    is_arrival: bool = False
    is_departure: bool = False
    is_stayover: bool = False


class HousekeepingUpdate(BaseModel):
    property_code: str
    room_number: str
    hk_status: str  # e.g. "vacant_clean", "vacant_dirty", "inspected", "ooo"
    # You can add hk_note: Optional[str] later if you want


# -------------------------------------------------------------------
# GET /housekeeping/rooms
# -------------------------------------------------------------------


@router.get("/rooms", response_model=List[HousekeepingRoom])
def get_housekeeping_rooms(
    property_code: str = Query(..., min_length=1),
    business_date: date = Query(...),
):
    """
    One line per room for the housekeeping board.

    business_date = Ethiopian hotel "business day" (same as front desk).
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # We reuse the same "rooms" + "bookings" structure you already have.
            # We DO NOT change how occupancy is calculated – this is only a view.
            cur.execute(
                """
                SELECT
                    r.property_code,
                    r.room_number,
                    r.room_type,
                    -- floor column is VARCHAR in your DB, cast if numeric
                    CASE
                        WHEN r.floor ~ '^[0-9]+$' THEN r.floor::int
                        ELSE NULL
                    END AS floor,
                    COALESCE(r.status, 'available') AS fo_status,
                    -- For now HK status = same column; front desk + HK see the same
                    COALESCE(r.status, 'available') AS hk_status,
                    b.id          AS current_booking_id,
                    b.guest_name  AS current_guest_name,
                    b.check_in_date   AS check_in,
                    b.check_out_date  AS check_out,
                    CASE WHEN b.check_in_date = %s THEN TRUE ELSE FALSE END AS is_arrival,
                    CASE WHEN b.check_out_date = %s THEN TRUE ELSE FALSE END AS is_departure,
                    CASE
                        WHEN b.check_in_date < %s
                         AND b.check_out_date > %s
                        THEN TRUE
                        ELSE FALSE
                    END AS is_stayover
                FROM rooms r
                LEFT JOIN bookings b
                    ON b.id = r.booking_id
                WHERE r.property_code = %s
                ORDER BY floor NULLS LAST, r.room_number;
                """,
                (
                    business_date,
                    business_date,
                    business_date,
                    business_date,
                    property_code,
                ),
            )

            rows = cur.fetchall()

    finally:
        conn.close()

    result: List[HousekeepingRoom] = []
    for row in rows:
        (
            prop_code,
            room_number,
            room_type,
            floor,
            fo_status,
            hk_status,
            booking_id,
            guest_name,
            check_in,
            check_out,
            is_arrival,
            is_departure,
            is_stayover,
        ) = row

        result.append(
            HousekeepingRoom(
                property_code=prop_code,
                room_number=room_number,
                room_type=room_type,
                floor=floor,
                fo_status=fo_status,
                hk_status=hk_status,
                current_booking_id=booking_id,
                current_guest_name=guest_name,
                check_in=check_in,
                check_out=check_out,
                is_arrival=is_arrival or False,
                is_departure=is_departure or False,
                is_stayover=is_stayover or False,
            )
        )

    return result


# -------------------------------------------------------------------
# POST /housekeeping/update
# -------------------------------------------------------------------


@router.post("/update")
def update_housekeeping_status(payload: HousekeepingUpdate):
    """
    Update the housekeeping status of a single room.

    For now, we simply write into rooms.status – the same field used by:
      - /rooms/status-list
      - /rooms/availability  (only cares about 'ooo' for out-of-order)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rooms
                SET
                    status = %s,
                    updated_at = now()
                WHERE property_code = %s
                  AND room_number = %s
                RETURNING property_code, room_number, status;
                """,
                (
                    payload.hk_status,
                    payload.property_code,
                    payload.room_number,
                ),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Room not found")

        conn.commit()

        return {
            "property_code": row[0],
            "room_number": row[1],
            "hk_status": row[2],
        }

    finally:
        conn.close()
