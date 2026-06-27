# guzo_backend/routers/availability.py

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from ..db.postgres_rooms import get_connection

router = APIRouter(prefix="/availability", tags=["availability"])


class AvailabilityResponse(BaseModel):
    property_code: str
    check_in: str
    check_out: str
    rooms_requested: int
    room_type: Optional[str] = None
    total_rooms: int
    overlapping_bookings: int
    out_of_order_rooms: int
    available_rooms: int
    is_available: bool
    min_available_rooms: int
    daily_breakdown: list[dict]


def _table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _room_status_expr(columns: set[str]) -> str:
    if "hk_status" in columns:
        return "hk_status"
    if "housekeeping_status" in columns:
        return "housekeeping_status"
    if "status" in columns:
        return "status"
    return "'clean'"


def _normalize_room_type(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned.upper() == "TBD":
        return None
    return cleaned


@router.get("/search", response_model=AvailabilityResponse)
def search_availability(
    property_code: str = Query(..., min_length=1),
    check_in: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    check_out: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    rooms: int = Query(1, ge=1),
    room_type: str | None = Query(None),
):
    try:
        check_in_date = date.fromisoformat(check_in)
        check_out_date = date.fromisoformat(check_out)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    if check_out_date <= check_in_date:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    requested_room_type = _normalize_room_type(room_type)

    with get_connection() as conn:
        room_columns = _table_columns(conn, "rooms")
        booking_columns = _table_columns(conn, "bookings")
        room_type_filter = ""
        booking_room_type_filter = ""
        params = {"property_code": property_code, "room_type": requested_room_type}
        if requested_room_type and "room_type" in room_columns:
            room_type_filter = "AND LOWER(COALESCE(room_type, '')) = LOWER(:room_type)"
        if requested_room_type and "room_type" in booking_columns:
            booking_room_type_filter = "AND LOWER(COALESCE(b.room_type, '')) = LOWER(:room_type)"
        booking_rooms_expr = "COALESCE(b.rooms, 1)" if "rooms" in booking_columns else "1"

        status_expr = _room_status_expr(room_columns)
        active_filter = "AND (is_active IS NULL OR is_active = TRUE)" if "is_active" in room_columns else ""
        total_row = conn.execute(
            text(f"""
                SELECT COUNT(*) AS total_rooms
                FROM rooms
                WHERE property_code = :property_code
                  {active_filter}
                  {room_type_filter}
            """),
            params,
        ).mappings().first()

        total_rooms = total_row["total_rooms"] if total_row else 0

        if total_rooms == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No rooms configured for property_code={property_code}",
            )

        daily_breakdown = []
        current = check_in_date
        while current < check_out_date:
            overlap_row = conn.execute(
                text(f"""
                SELECT COALESCE(SUM({booking_rooms_expr}), 0) AS overlapping
                FROM bookings b
                WHERE b.property_code = :property_code
                  AND LOWER(COALESCE(b.booking_status, '')) IN (
                    'confirmed',
                    'reserved',
                    'pending_guarantee',
                    'in_house',
                    'checked_in'
                  )
                  AND b.check_in_date <= :stay_date
                  AND b.check_out_date > :stay_date
                  {booking_room_type_filter}
                """),
                {**params, "stay_date": current},
            ).mappings().first()
            ooo_row = conn.execute(
                text(f"""
                SELECT COUNT(*) AS out_of_order
                FROM rooms
                WHERE property_code = :property_code
                  {active_filter}
                  {room_type_filter}
                  AND LOWER(COALESCE({status_expr}, '')) IN (
                    'out_of_order',
                    'out of order',
                    'out_of_service',
                    'out of service',
                    'maintenance',
                    'service_in_progress',
                    'service in progress',
                    'ooo'
                  )
                """),
                params,
            ).mappings().first()
            overlapping = int((overlap_row or {}).get("overlapping") or 0)
            out_of_order = int((ooo_row or {}).get("out_of_order") or 0)
            available = max(int(total_rooms) - overlapping - out_of_order, 0)
            daily_breakdown.append(
                {
                    "date": current.isoformat(),
                    "total_rooms": int(total_rooms),
                    "overlapping_bookings": overlapping,
                    "out_of_order_rooms": out_of_order,
                    "available_rooms": available,
                    "is_available": available >= rooms,
                }
            )
            current += timedelta(days=1)

        min_available = min((day["available_rooms"] for day in daily_breakdown), default=0)
        max_overlap = max((day["overlapping_bookings"] for day in daily_breakdown), default=0)
        max_ooo = max((day["out_of_order_rooms"] for day in daily_breakdown), default=0)

        return AvailabilityResponse(
            property_code=property_code,
            check_in=check_in,
            check_out=check_out,
            rooms_requested=rooms,
            room_type=requested_room_type,
            total_rooms=total_rooms,
            overlapping_bookings=max_overlap,
            out_of_order_rooms=max_ooo,
            available_rooms=min_available,
            is_available=min_available >= rooms,
            min_available_rooms=min_available,
            daily_breakdown=daily_breakdown,
        )
