# -*- coding: utf-8 -*-
"""
guzo_backend.api.rooms_housekeeping_api

Housekeeping Board API for Guzo Guest Assist.

This version:
- Derives occupancy from the `bookings` table (stays overlapping business_date)
- Stores HK status per room/date/property in `housekeeping_status`
- Uses get_db_connection() and SQLAlchemy text() (no .cursor())
- If housekeeping_status table does NOT exist, we treat it as empty
  (no 500 error for GET /rooms/status-board).
- Exposes:
    GET  /rooms/housekeeping        -> list housekeeping rooms for a date
    GET  /rooms/status-board        -> same payload, used by dashboard UI
    POST /rooms/housekeeping/mark-clean
    POST /rooms/housekeeping/mark-dirty
    POST /rooms/housekeeping/mark-out-of-order
    POST /rooms/housekeeping/mark-in-service
"""

from datetime import date
from typing import List, Optional, Dict, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from guzo_backend.core.postgres_db import get_db_connection

router = APIRouter(
    prefix="/rooms",
    tags=["rooms", "housekeeping"],
)


# ----------------------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------------------


class HousekeepingRoom(BaseModel):
    """
    Shape returned to the frontend HousekeepingBoard.tsx.
    """
    room_number: str
    property_code: str
    floor: Optional[int] = None
    hk_status: str              # e.g. "occupied_clean", "vacant_clean"
    business_date: date
    is_occupied: bool

    # Optional live guest info from bookings
    guest_name: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None


class HKActionPayload(BaseModel):
    """
    Body for Mark Clean / Dirty / OOO / In Service endpoints.
    business_date is optional – defaults to 'today' if not provided.
    """
    room_number: str
    property_code: str
    business_date: Optional[date] = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _normalize_status(hk_status: str, is_occupied: bool) -> str:
    """
    Ensure hk_status is one of our known values.
    If unknown, use a sensible default based on occupancy.
    """
    allowed = {
        "vacant_clean",
        "vacant_dirty",
        "occupied_clean",
        "occupied_dirty",
        "out_of_order",
        "in_service",
    }
    if hk_status in allowed:
        return hk_status

    # Fallbacks
    if is_occupied:
        return "occupied_clean"
    return "vacant_clean"


def _load_housekeeping_rooms_for_date(
    business_date: date,
    property_code: str,
) -> List[HousekeepingRoom]:
    """
    Core logic (no .cursor(), using get_db_connection):

    1) Load occupancy from bookings:
         - check_in_date <= business_date < check_out_date
         - room_number IS NOT NULL
    2) Try to load housekeeping_status rows for that business_date.
         - If the housekeeping_status table does NOT exist,
           treat it as empty (no rows) instead of raising 500.
    3) For each (property_code, room_number) seen in either:
         - Determine is_occupied + guest info from bookings.
         - Determine hk_status from housekeeping_status if present,
           else derive default from occupancy.
    """

    # Key type: (property_code, room_number)
    OccKey = Tuple[str, str]

    occupancy: Dict[OccKey, Dict] = {}
    hk_map: Dict[OccKey, str] = {}

    try:
        # --------------------------------------------------------------
        # 1) Load occupancy from bookings
        # --------------------------------------------------------------
        bookings_sql = """
            SELECT
                room_number,
                property_code,
                guest_name,
                check_in_date,
                check_out_date
            FROM bookings
            WHERE
                room_number IS NOT NULL
                AND check_in_date <= :business_date
                AND check_out_date > :business_date
        """
        bookings_params = {"business_date": business_date}

        if property_code != "all":
            bookings_sql += " AND property_code = :property_code"
            bookings_params["property_code"] = property_code

        with get_db_connection() as conn:
            bookings_result = conn.execute(text(bookings_sql), bookings_params)
            booking_rows = bookings_result.fetchall()

        for (
            room_number,
            property_code_db,
            guest_name,
            check_in_date,
            check_out_date,
        ) in booking_rows:
            key: OccKey = (property_code_db, room_number)
            occupancy[key] = {
                "guest_name": guest_name,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "is_occupied": True,
            }

        # --------------------------------------------------------------
        # 2) Try to load housekeeping_status overrides
        # --------------------------------------------------------------
        hk_sql = """
            SELECT
                property_code,
                room_number,
                hk_status
            FROM housekeeping_status
            WHERE business_date = :business_date
        """
        hk_params = {"business_date": business_date}

        if property_code != "all":
            hk_sql += " AND property_code = :property_code"
            hk_params["property_code"] = property_code

        hk_rows = []
        try:
            with get_db_connection() as conn:
                hk_result = conn.execute(text(hk_sql), hk_params)
                hk_rows = hk_result.fetchall()
        except Exception as e:
            # If the error is that the table doesn't exist, treat as empty
            msg = repr(e)
            if "UndefinedTable" in msg or 'relation "housekeeping_status"' in msg:
                hk_rows = []
            else:
                raise

        for (prop_code, room_number, hk_status) in hk_rows:
            key: OccKey = (prop_code, room_number)
            hk_map[key] = hk_status

    except HTTPException:
        # Pass through our own HTTPExceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading housekeeping rooms: {e}",
        )

    # ----------------------------------------------------------
    # 3) Merge occupancy + housekeeping_status
    # ----------------------------------------------------------

    rooms: List[HousekeepingRoom] = []
    all_keys = set(occupancy.keys()) | set(hk_map.keys())

    for (prop_code, room_number) in sorted(all_keys):
        occ = occupancy.get((prop_code, room_number))
        hk_status_raw = hk_map.get((prop_code, room_number))

        is_occupied = bool(occ and occ.get("is_occupied", False))
        guest_name = occ.get("guest_name") if occ else None
        check_in_date = occ.get("check_in_date") if occ else None
        check_out_date = occ.get("check_out_date") if occ else None

        # If we have an explicit hk_status row, use it; otherwise derive
        if hk_status_raw is not None:
            hk_status = _normalize_status(hk_status_raw, is_occupied)
        else:
            hk_status = "occupied_clean" if is_occupied else "vacant_clean"

        # Simple floor inference: "305" -> 3
        floor: Optional[int]
        if room_number and room_number[0].isdigit():
            floor = int(room_number[0])
        else:
            floor = None

        rooms.append(
            HousekeepingRoom(
                room_number=room_number,
                property_code=prop_code,
                floor=floor,
                hk_status=hk_status,
                business_date=business_date,
                is_occupied=is_occupied,
                guest_name=guest_name,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
            )
        )

    return rooms


def _set_housekeeping_status(
    business_date: date,
    property_code: str,
    room_number: str,
    hk_status: str,
) -> None:
    """
    Insert or update a housekeeping_status record
    using get_db_connection and SQLAlchemy text().

    NOTE: If the table does not exist, this may raise an error when
    you first try to mark clean/dirty; that can be handled separately.
    For now, the goal is that GET /rooms/status-board never 500s.
    """
    hk_status = _normalize_status(hk_status, is_occupied=False)

    upsert_sql = """
        INSERT INTO housekeeping_status (
            business_date,
            property_code,
            room_number,
            hk_status
        )
        VALUES (:business_date, :property_code, :room_number, :hk_status)
        ON CONFLICT (business_date, property_code, room_number)
        DO UPDATE SET
            hk_status = EXCLUDED.hk_status,
            updated_at = now()
    """

    params = {
        "business_date": business_date,
        "property_code": property_code,
        "room_number": room_number,
        "hk_status": hk_status,
    }

    try:
        with get_db_connection() as conn:
            conn.execute(text(upsert_sql), params)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving housekeeping status: {e}",
        )


# ----------------------------------------------------------------------
# Public endpoints
# ----------------------------------------------------------------------


@router.get("/housekeeping", response_model=List[HousekeepingRoom])
def list_housekeeping_rooms(
    date_str: str = Query(..., alias="date"),
    property_code: str = Query("all"),
):
    """
    Return housekeeping status for rooms for a given business date.
    Used as base endpoint; dashboard uses /rooms/status-board, but both
    share the same logic.
    """
    try:
        business_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid 'date' format. Expected YYYY-MM-DD.",
        )

    return _load_housekeeping_rooms_for_date(business_date, property_code)


@router.get("/status-board", response_model=List[HousekeepingRoom])
def rooms_status_board(
    date_str: str = Query(..., alias="date"),
    property_code: str = Query("all"),
):
    """
    Main endpoint consumed by HousekeepingBoard.tsx.
    """
    try:
        business_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid 'date' format. Expected YYYY-MM-DD.",
        )

    return _load_housekeeping_rooms_for_date(business_date, property_code)


# ----------------------------------------------------------------------
# Housekeeping action endpoints
# ----------------------------------------------------------------------


@router.post("/housekeeping/mark-clean")
def mark_room_clean(payload: HKActionPayload):
    """
    Mark a room as Vacant / Clean (or stay as 'occupied_clean' if we later
    decide to tie it to occupancy).
    """
    business_date = payload.business_date or date.today()
    _set_housekeeping_status(
        business_date=business_date,
        property_code=payload.property_code,
        room_number=payload.room_number,
        hk_status="vacant_clean",
    )
    return {"status": "ok", "hk_status": "vacant_clean"}


@router.post("/housekeeping/mark-dirty")
def mark_room_dirty(payload: HKActionPayload):
    business_date = payload.business_date or date.today()
    _set_housekeeping_status(
        business_date=business_date,
        property_code=payload.property_code,
        room_number=payload.room_number,
        hk_status="vacant_dirty",
    )
    return {"status": "ok", "hk_status": "vacant_dirty"}


@router.post("/housekeeping/mark-out-of-order")
def mark_room_out_of_order(payload: HKActionPayload):
    business_date = payload.business_date or date.today()
    _set_housekeeping_status(
        business_date=business_date,
        property_code=payload.property_code,
        room_number=payload.room_number,
        hk_status="out_of_order",
    )
    return {"status": "ok", "hk_status": "out_of_order"}


@router.post("/housekeeping/mark-in-service")
def mark_room_in_service(payload: HKActionPayload):
    business_date = payload.business_date or date.today()
    _set_housekeeping_status(
        business_date=business_date,
        property_code=payload.property_code,
        room_number=payload.room_number,
        hk_status="in_service",
    )
    return {"status": "ok", "hk_status": "in_service"}
