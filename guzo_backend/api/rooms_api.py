# guzo_backend/api/rooms_api.py
#
# Rooms inventory & simple availability endpoints.
#
# Endpoints:
#   GET /rooms
#   GET /rooms/availability
#
# Uses:
#   - get_db_connection()
#   - verify_admin_token()

from __future__ import annotations

from datetime import date
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from guzo_backend.dependencies import get_db_connection, verify_admin_token

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)


# -----------------------------------------------------------
# GET /rooms  – list room inventory
# -----------------------------------------------------------


@router.get(
    "",
    summary="List rooms",
    description="List rooms for all properties or a single property_code.",
)
def list_rooms(
    _admin_ok: None = Depends(verify_admin_token),
    property_code: Optional[str] = Query(
        None,
        description="Hotel property_code (e.g. 'DRE001'). If omitted, returns all rooms.",
    ),
) -> Dict[str, Any]:
    where_sql = ""
    params: list = []

    if property_code:
        where_sql = "WHERE r.property_code = %s"
        params.append(property_code)

    sql = f"""
        SELECT
            r.id,
            r.hotel_id,
            r.property_code,
            r.room_number,
            r.room_type,
            r.floor,
            r.status,
            r.booking_id,
            r.created_at,
            r.updated_at
        FROM rooms AS r
        {where_sql}
        ORDER BY r.property_code, r.room_number
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading rooms: {exc}",
        ) from exc

    return {
        "count": len(rows),
        "items": rows,
    }


# -----------------------------------------------------------
# GET /rooms/availability – simple availability per room_type
# -----------------------------------------------------------


@router.get(
    "/availability",
    summary="Check availability by date",
    description=(
        "Return total rooms and booked rooms per room_type for a given "
        "property_code and date. Uses rooms + bookings tables."
    ),
)
def room_availability(
    _admin_ok: None = Depends(verify_admin_token),
    property_code: str = Query(
        ...,
        description="Hotel property_code (e.g. 'DRE001').",
    ),
    target_date: date = Query(
        ...,
        description="Date to check, e.g. 2025-11-23.",
    ),
) -> Dict[str, Any]:
    """
    Simple availability per room_type for one day.

    Logic:
      - total rooms per type from rooms table
      - active bookings where:
          check_in_date <= target_date < check_out_date
        and booking_status NOT cancelled
    """

    # 1) Total rooms per room_type
    sql_total = """
        SELECT
            room_type,
            COUNT(*) AS rooms_total
        FROM rooms
        WHERE property_code = %s
        GROUP BY room_type
    """

    # 2) Booked rooms per room_type for that date
    sql_booked = """
        SELECT
            room_type,
            COUNT(*) AS rooms_booked
        FROM bookings
        WHERE property_code = %s
          AND check_in_date <= %s
          AND check_out_date > %s
          AND (booking_status IS NULL
               OR LOWER(booking_status) NOT LIKE 'cancel%%')
        GROUP BY room_type
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # total rooms
                cur.execute(sql_total, [property_code])
                total_rows = cur.fetchall()

                # booked rooms
                cur.execute(sql_booked, [property_code, target_date, target_date])
                booked_rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading availability: {exc}",
        ) from exc

    total_map: Dict[str, int] = {
        row["room_type"]: int(row["rooms_total"]) for row in total_rows
    }
    booked_map: Dict[str, int] = {
        row["room_type"]: int(row["rooms_booked"]) for row in booked_rows
    }

    availability: List[Dict[str, Any]] = []
    for room_type, rooms_total in total_map.items():
        rooms_booked = booked_map.get(room_type, 0)
        rooms_available = max(rooms_total - rooms_booked, 0)

        availability.append(
            {
                "room_type": room_type,
                "rooms_total": rooms_total,
                "rooms_booked": rooms_booked,
                "rooms_available": rooms_available,
            }
        )

    return {
        "property_code": property_code,
        "date": target_date,
        "availability": availability,
    }
