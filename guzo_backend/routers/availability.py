# guzo_backend/routers/availability.py
#
# Simple availability check for bots / web:
#   GET /availability/search?property_code=DRE001&check_in=2025-12-01&check_out=2025-12-03&rooms=1
#
# Logic (v1):
#   - count total rooms for property_code (from rooms table)
#   - count bookings that overlap the date range (confirmed + in_house)
#   - assume each booking uses 1 room
#   - available_rooms = total_rooms - overlapping_bookings

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from ..db.postgres_rooms import get_connection

router = APIRouter(prefix="/availability", tags=["availability"])


class AvailabilityResponse(BaseModel):
    property_code: str
    check_in: str
    check_out: str
    rooms_requested: int
    total_rooms: int
    overlapping_bookings: int
    available_rooms: int
    is_available: bool


@router.get("/search", response_model=AvailabilityResponse)
def search_availability(
    property_code: str = Query(..., min_length=1),
    # Pydantic v2: use `pattern` instead of `regex`
    check_in: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    check_out: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    rooms: int = Query(1, ge=1),
):
    """
    Check if a property has enough free rooms for a date range.

    NOTE:
      - v1 assumes:
           * each booking uses 1 room
           * we consider bookings with status in ('confirmed', 'in_house')
      - later we can extend to room_type, number_of_rooms, etc.
    """

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Count total rooms for this property
                cur.execute(
                    """
                    SELECT COUNT(*) AS total_rooms
                    FROM rooms
                    WHERE property_code = %s
                    """,
                    (property_code,),
                )
                row = cur.fetchone()
                total_rooms = row["total_rooms"] if row else 0

                if total_rooms == 0:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No rooms configured for property_code={property_code}",
                    )

                # 2) Count overlapping bookings in this date range for this property
                #
                # Overlap condition:
                #   booking.check_in_date < check_out
                #   AND booking.check_out_date > check_in
                #
                # We consider only confirmed and in_house bookings for availability.
                cur.execute(
                    """
                    SELECT COUNT(*) AS overlapping
                    FROM bookings b
                    WHERE b.property_code = %s
                      AND b.booking_status IN ('confirmed', 'in_house')
                      AND b.check_in_date < %s::date
                      AND b.check_out_date > %s::date
                    """,
                    (property_code, check_out, check_in),
                )
                row2 = cur.fetchone()
                overlapping = row2["overlapping"] if row2 else 0

                available_rooms = max(total_rooms - overlapping, 0)
                is_available = available_rooms >= rooms

                return AvailabilityResponse(
                    property_code=property_code,
                    check_in=check_in,
                    check_out=check_out,
                    rooms_requested=rooms,
                    total_rooms=total_rooms,
                    overlapping_bookings=overlapping,
                    available_rooms=available_rooms,
                    is_available=is_available,
                )
    finally:
        conn.close()
