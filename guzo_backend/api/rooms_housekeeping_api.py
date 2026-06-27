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

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.core.postgres_db import get_db_connection
from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission, require_property_access

router = APIRouter(
    prefix="/rooms",
    tags=["rooms", "housekeeping"],
)
legacy_router = APIRouter(tags=["housekeeping"])


# ----------------------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------------------


class HousekeepingRoom(BaseModel):
    """
    Shape returned to the frontend HousekeepingBoard.tsx.
    """
    room_number: str
    property_code: str
    room_type: Optional[str] = None
    floor: Optional[int] = None
    hk_status: str              # e.g. "occupied_clean", "vacant_clean"
    business_date: date
    is_occupied: bool

    # Optional live guest info from bookings
    guest_name: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    assigned_to: Optional[str] = None
    maintenance_note: Optional[str] = None
    out_of_order_reason: Optional[str] = None
    lost_item_note: Optional[str] = None
    inspected_by: Optional[str] = None
    inspected_at: Optional[str] = None


class HKActionPayload(BaseModel):
    """
    Body for Mark Clean / Dirty / OOO / In Service endpoints.
    business_date is optional – defaults to 'today' if not provided.
    """
    room_number: str
    property_code: str
    business_date: Optional[date] = None
    note: Optional[str] = None
    assigned_to: Optional[str] = None
    maintenance_note: Optional[str] = None
    out_of_order_reason: Optional[str] = None
    lost_item_note: Optional[str] = None


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
        "inspected",
        "vacant_inspected",
        "out_of_order",
        "out_of_service",
        "maintenance",
        "in_service",
        "service_in_progress",
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

    property_code = str(property_code or "").strip().upper()
    if not property_code or property_code in {"ALL", "*"}:
        raise ValueError("property_code is required for housekeeping room loads")

    # Key type: (property_code, room_number)
    OccKey = Tuple[str, str]

    occupancy: Dict[OccKey, Dict] = {}
    hk_map: Dict[OccKey, str] = {}
    room_inventory: Dict[OccKey, Dict] = {}

    try:
        # --------------------------------------------------------------
        # 0) Load configured rooms inventory. This is the source of truth
        #    for total rooms, including vacant rooms without bookings.
        # --------------------------------------------------------------
        rooms_sql = """
            SELECT
                property_code,
                room_number,
                room_type,
                floor
            FROM rooms
            WHERE 1 = 1
        """
        rooms_params = {}

        rooms_sql += " AND property_code = :property_code"
        rooms_params["property_code"] = property_code

        try:
            with get_db_connection() as conn:
                rooms_result = conn.execute(text(rooms_sql), rooms_params)
                room_rows = rooms_result.fetchall()
        except Exception as e:
            msg = repr(e)
            if "UndefinedTable" in msg or 'relation "rooms"' in msg:
                room_rows = []
            else:
                raise

        for (prop_code, room_number, room_type, floor) in room_rows:
            key: OccKey = (prop_code, str(room_number))
            room_inventory[key] = {
                "room_type": room_type,
                "floor": floor,
            }

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
        try:
            with get_db_connection() as conn:
                for column_sql in [
                    "ADD COLUMN IF NOT EXISTS id BIGSERIAL",
                    "ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(150)",
                    "ADD COLUMN IF NOT EXISTS maintenance_note TEXT",
                    "ADD COLUMN IF NOT EXISTS out_of_order_reason TEXT",
                    "ADD COLUMN IF NOT EXISTS lost_item_note TEXT",
                    "ADD COLUMN IF NOT EXISTS inspected_by VARCHAR(150)",
                    "ADD COLUMN IF NOT EXISTS inspected_at TIMESTAMP",
                ]:
                    conn.execute(text(f"ALTER TABLE housekeeping_status {column_sql}"))
                if hasattr(conn, "commit"):
                    conn.commit()
        except Exception as e:
            msg = repr(e)
            if "UndefinedTable" not in msg and 'relation "housekeeping_status"' not in msg:
                raise

        hk_sql = """
            SELECT
                property_code,
                room_number,
                hk_status,
                assigned_to,
                maintenance_note,
                out_of_order_reason,
                lost_item_note,
                inspected_by,
                inspected_at
            FROM housekeeping_status
            WHERE business_date = :business_date
        """
        hk_params = {"business_date": business_date}

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

        for (
            prop_code,
            room_number,
            hk_status,
            assigned_to,
            maintenance_note,
            out_of_order_reason,
            lost_item_note,
            inspected_by,
            inspected_at,
        ) in hk_rows:
            key: OccKey = (prop_code, room_number)
            hk_map[key] = {
                "hk_status": hk_status,
                "assigned_to": assigned_to,
                "maintenance_note": maintenance_note,
                "out_of_order_reason": out_of_order_reason,
                "lost_item_note": lost_item_note,
                "inspected_by": inspected_by,
                "inspected_at": inspected_at,
            }

    except HTTPException:
        # Pass through our own HTTPExceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading housekeeping rooms: {e}",
        )

    # ----------------------------------------------------------
    # 3) Merge inventory + occupancy + housekeeping_status.
    #
    # If configured room inventory exists, it is the source of truth
    # for the Housekeeping board room count. Old housekeeping_status
    # rows or historical bookings for rooms no longer in inventory
    # must not inflate Total Rooms.
    # ----------------------------------------------------------

    rooms: List[HousekeepingRoom] = []
    if room_inventory:
        all_keys = set(room_inventory.keys())
    else:
        all_keys = set(occupancy.keys()) | set(hk_map.keys())

    for (prop_code, room_number) in sorted(all_keys):
        occ = occupancy.get((prop_code, room_number))
        inventory = room_inventory.get((prop_code, room_number), {})
        hk_row = hk_map.get((prop_code, room_number), {})
        hk_status_raw = hk_row.get("hk_status") if isinstance(hk_row, dict) else hk_row

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
        floor_raw = inventory.get("floor")
        if floor_raw is not None:
            try:
                floor = int(floor_raw)
            except (TypeError, ValueError):
                floor = None
        elif room_number and room_number[0].isdigit():
            floor = int(room_number[0])
        else:
            floor = None

        rooms.append(
            HousekeepingRoom(
                room_number=room_number,
                property_code=prop_code,
                room_type=inventory.get("room_type"),
                floor=floor,
                hk_status=hk_status,
                business_date=business_date,
                is_occupied=is_occupied,
                guest_name=guest_name,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                assigned_to=hk_row.get("assigned_to") if isinstance(hk_row, dict) else None,
                maintenance_note=hk_row.get("maintenance_note") if isinstance(hk_row, dict) else None,
                out_of_order_reason=hk_row.get("out_of_order_reason") if isinstance(hk_row, dict) else None,
                lost_item_note=hk_row.get("lost_item_note") if isinstance(hk_row, dict) else None,
                inspected_by=hk_row.get("inspected_by") if isinstance(hk_row, dict) else None,
                inspected_at=hk_row.get("inspected_at").isoformat() if isinstance(hk_row, dict) and hk_row.get("inspected_at") else None,
            )
        )

    return rooms


def _table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
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


def _ensure_housekeeping_status_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS housekeeping_status (
                id SERIAL PRIMARY KEY,
                business_date DATE NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                room_number VARCHAR(20) NOT NULL,
                hk_status VARCHAR(50) NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (business_date, property_code, room_number)
            )
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE housekeeping_status
            ADD COLUMN IF NOT EXISTS note TEXT
            """
        )
    )
    for column_sql in [
        "ADD COLUMN IF NOT EXISTS id BIGSERIAL",
        "ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(150)",
        "ADD COLUMN IF NOT EXISTS maintenance_note TEXT",
        "ADD COLUMN IF NOT EXISTS out_of_order_reason TEXT",
        "ADD COLUMN IF NOT EXISTS lost_item_note TEXT",
        "ADD COLUMN IF NOT EXISTS inspected_by VARCHAR(150)",
        "ADD COLUMN IF NOT EXISTS inspected_at TIMESTAMP",
    ]:
        db.execute(text(f"ALTER TABLE housekeeping_status {column_sql}"))


def _sync_live_room_status(
    db: Session,
    *,
    property_code: str,
    room_number: str,
    hk_status: str,
) -> None:
    columns = _table_columns(db, "rooms")
    status_column = None
    if "hk_status" in columns:
        status_column = "hk_status"
    elif "housekeeping_status" in columns:
        status_column = "housekeeping_status"
    elif "status" in columns:
        status_column = "status"

    updates = []
    if status_column:
        updates.append(f"{status_column} = :hk_status")
    if "is_occupied" in columns:
        if hk_status.startswith("vacant"):
            updates.append("is_occupied = FALSE")
        elif hk_status.startswith("occupied"):
            updates.append("is_occupied = TRUE")
    if not updates:
        return

    db.execute(
        text(
            f"""
            UPDATE rooms
            SET {", ".join(updates)}
            WHERE property_code = :property_code
              AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
            """
        ),
        {
            "property_code": property_code,
            "room_number": room_number,
            "hk_status": hk_status,
        },
    )


def _room_is_occupied_on_date(
    db: Session,
    *,
    business_date: date,
    property_code: str,
    room_number: str,
) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM bookings
            WHERE property_code = :property_code
              AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
              AND check_in_date <= :business_date
              AND check_out_date > :business_date
              AND LOWER(COALESCE(booking_status, '')) IN (
                'in_house',
                'checked_in'
              )
            LIMIT 1
            """
        ),
        {
            "business_date": business_date,
            "property_code": property_code,
            "room_number": room_number,
        },
    ).first()
    return bool(row)


def _set_housekeeping_status(
    db: Session,
    business_date: date,
    property_code: str,
    room_number: str,
    hk_status: str,
    *,
    user_email: str | None = None,
    action: str = "room_status_updated",
    note: str | None = None,
    assigned_to: str | None = None,
    maintenance_note: str | None = None,
    out_of_order_reason: str | None = None,
    lost_item_note: str | None = None,
) -> None:
    property_code = property_code.strip().upper()
    is_occupied = _room_is_occupied_on_date(
        db,
        business_date=business_date,
        property_code=property_code,
        room_number=room_number,
    )
    if hk_status == "vacant_clean" and is_occupied:
        hk_status = "occupied_clean"
    if hk_status == "vacant_dirty" and is_occupied:
        hk_status = "occupied_dirty"
    hk_status = _normalize_status(hk_status, is_occupied=is_occupied)
    _ensure_housekeeping_status_table(db)

    db.execute(
        text(
            """
            INSERT INTO housekeeping_status (
                business_date,
                property_code,
                room_number,
                hk_status,
                note,
                assigned_to,
                maintenance_note,
                out_of_order_reason,
                lost_item_note,
                inspected_by,
                inspected_at
            )
            VALUES (
                :business_date,
                :property_code,
                :room_number,
                :hk_status,
                :note,
                :assigned_to,
                :maintenance_note,
                :out_of_order_reason,
                :lost_item_note,
                :inspected_by,
                :inspected_at
            )
            ON CONFLICT (business_date, property_code, room_number)
            DO UPDATE SET
                hk_status = EXCLUDED.hk_status,
                note = COALESCE(EXCLUDED.note, housekeeping_status.note),
                assigned_to = COALESCE(EXCLUDED.assigned_to, housekeeping_status.assigned_to),
                maintenance_note = COALESCE(EXCLUDED.maintenance_note, housekeeping_status.maintenance_note),
                out_of_order_reason = COALESCE(EXCLUDED.out_of_order_reason, housekeeping_status.out_of_order_reason),
                lost_item_note = COALESCE(EXCLUDED.lost_item_note, housekeeping_status.lost_item_note),
                inspected_by = COALESCE(EXCLUDED.inspected_by, housekeeping_status.inspected_by),
                inspected_at = COALESCE(EXCLUDED.inspected_at, housekeeping_status.inspected_at),
                updated_at = now()
            """
        ),
        {
            "business_date": business_date,
            "property_code": property_code,
            "room_number": room_number,
            "hk_status": hk_status,
            "note": note,
            "assigned_to": assigned_to,
            "maintenance_note": maintenance_note,
            "out_of_order_reason": out_of_order_reason,
            "lost_item_note": lost_item_note,
            "inspected_by": user_email if hk_status in {"inspected", "vacant_inspected"} else None,
            "inspected_at": date.today() if hk_status in {"inspected", "vacant_inspected"} else None,
        },
    )
    _sync_live_room_status(
        db,
        property_code=property_code,
        room_number=room_number,
        hk_status=hk_status,
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=user_email,
        module="housekeeping",
        action=action,
        record_type="room",
        record_id=room_number,
        new_value={
            "business_date": business_date.isoformat(),
            "room_number": room_number,
            "hk_status": hk_status,
            "note": note,
            "assigned_to": assigned_to,
            "maintenance_note": maintenance_note,
            "out_of_order_reason": out_of_order_reason,
            "lost_item_note": lost_item_note,
        },
    )


# ----------------------------------------------------------------------
# Public endpoints
# ----------------------------------------------------------------------


@router.get("/housekeeping", response_model=List[HousekeepingRoom])
def list_housekeeping_rooms(
    date_str: str = Query(..., alias="date"),
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
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

    property_code = property_code.strip().upper()
    try:
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    except HTTPException as exc:
        if exc.status_code == 404:
            return []
        raise
    return _load_housekeeping_rooms_for_date(business_date, property_code)


@router.get("/status-board", response_model=List[HousekeepingRoom])
def rooms_status_board(
    date_str: str = Query(..., alias="date"),
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
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

    property_code = property_code.strip().upper()
    try:
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    except HTTPException as exc:
        if exc.status_code == 404:
            return []
        raise
    return _load_housekeeping_rooms_for_date(business_date, property_code)


# ----------------------------------------------------------------------
# Housekeeping action endpoints
# ----------------------------------------------------------------------


def _run_housekeeping_action(
    payload: HKActionPayload,
    *,
    db: Session,
    user_email: str | None,
    permission_key: str,
    hk_status: str,
    audit_action: str,
):
    business_date = payload.business_date or date.today()
    property_code = payload.property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key=permission_key,
        property_code=property_code,
        user_email=user_email,
    )
    _set_housekeeping_status(
        db,
        business_date=business_date,
        property_code=property_code,
        room_number=payload.room_number,
        hk_status=hk_status,
        user_email=actor["email"],
        action=audit_action,
        note=payload.note,
        assigned_to=payload.assigned_to,
        maintenance_note=payload.maintenance_note,
        out_of_order_reason=payload.out_of_order_reason,
        lost_item_note=payload.lost_item_note,
    )
    db.commit()
    return {"status": "ok", "hk_status": hk_status}


@legacy_router.post("/housekeeping/mark-clean")
@router.post("/housekeeping/mark-clean")
def mark_room_clean(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.mark_cleaned",
        hk_status="vacant_clean",
        audit_action="room_marked_cleaned",
    )


@legacy_router.post("/housekeeping/mark-dirty")
@router.post("/housekeeping/mark-dirty")
def mark_room_dirty(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.mark_cleaned",
        hk_status="vacant_dirty",
        audit_action="room_marked_dirty",
    )


@legacy_router.post("/housekeeping/mark-out-of-order")
@router.post("/housekeeping/mark-out-of-order")
def mark_room_out_of_order(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.room_status_override",
        hk_status="out_of_order",
        audit_action="room_marked_out_of_order",
    )


@legacy_router.post("/housekeeping/mark-in-service")
@router.post("/housekeeping/mark-in-service")
def mark_room_in_service(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.mark_cleaned",
        hk_status="service_in_progress",
        audit_action="room_cleaning_started",
    )


@legacy_router.post("/housekeeping/mark-inspected")
@router.post("/housekeeping/mark-inspected")
def mark_room_inspected(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.mark_inspected",
        hk_status="vacant_inspected",
        audit_action="room_marked_inspected",
    )


@legacy_router.post("/housekeeping/mark-out-of-service")
@router.post("/housekeeping/mark-out-of-service")
def mark_room_out_of_service(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.room_status_override",
        hk_status="out_of_service",
        audit_action="room_marked_out_of_service",
    )


@legacy_router.post("/housekeeping/mark-maintenance")
@router.post("/housekeeping/mark-maintenance")
def mark_room_maintenance(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _run_housekeeping_action(
        payload,
        db=db,
        user_email=x_pms_user_email,
        permission_key="housekeeping.room_status_override",
        hk_status="maintenance",
        audit_action="room_marked_maintenance",
    )


@legacy_router.post("/housekeeping/assign-attendant")
@router.post("/housekeeping/assign-attendant")
def assign_room_attendant(
    payload: HKActionPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    business_date = payload.business_date or date.today()
    property_code = payload.property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="housekeeping.room_status_override",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    if not payload.assigned_to:
        raise HTTPException(status_code=400, detail="assigned_to is required")

    _ensure_housekeeping_status_table(db)
    existing = db.execute(
        text(
            """
            SELECT hk_status
            FROM housekeeping_status
            WHERE business_date = :business_date
              AND property_code = :property_code
              AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
            LIMIT 1
            """
        ),
        {
            "business_date": business_date,
            "property_code": property_code,
            "room_number": payload.room_number,
        },
    ).first()
    hk_status = existing[0] if existing else "vacant_dirty"
    _set_housekeeping_status(
        db,
        business_date=business_date,
        property_code=property_code,
        room_number=payload.room_number,
        hk_status=hk_status,
        user_email=actor["email"],
        action="room_attendant_assigned",
        note=payload.note,
        assigned_to=payload.assigned_to,
    )
    db.commit()
    return {"status": "ok", "assigned_to": payload.assigned_to, "hk_status": hk_status}
