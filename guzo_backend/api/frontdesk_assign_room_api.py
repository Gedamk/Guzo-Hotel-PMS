# guzo_backend/api/frontdesk_assign_room_api.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from guzo_backend.dependencies import get_db  # <-- we use the shared DB dependency
from guzo_backend.services.audit_log_service import record_audit_log
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission


router = APIRouter(
    prefix="/frontdesk",
    tags=["frontdesk-assign-room"],
)


class AssignRoomPayload(BaseModel):
    booking_id: int
    property_code: str
    room_number: str


class BookingResponse(BaseModel):
    id: int
    guest_name: str
    check_in_date: str  # ISO date
    check_out_date: str  # ISO date
    booking_status: str
    property_code: str
    room_number: str


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


def _room_status_expression(columns: set[str]) -> str:
    if "hk_status" in columns:
        return "hk_status"
    if "housekeeping_status" in columns:
        return "housekeeping_status"
    if "status" in columns:
        return "status"
    return "'unknown'"


ASSIGNABLE_ROOM_STATUSES = {
    "available",
    "clean",
    "inspected",
    "vacant_clean",
    "vacant_inspected",
}


def _is_assignable_room_status(room_status: str) -> bool:
    normalized = str(room_status or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in ASSIGNABLE_ROOM_STATUSES


@router.post("/assign-room", response_model=BookingResponse, status_code=status.HTTP_200_OK)
def assign_room(
    payload: AssignRoomPayload,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
) -> BookingResponse:
    """
    Assign a room number to a booking without checking the guest in.

    This updates the bookings table:
      - room_number = :room_number

    Check-in is a separate controlled action that validates guarantee and
    housekeeping readiness before changing booking_status to in_house.
    """
    try:
        property_code = payload.property_code.strip().upper()
        actor = require_pms_permission(
            db,
            permission_key="frontdesk.room_move",
            property_code=property_code,
            user_email=x_pms_user_email,
        )
        room_columns = _table_columns(db, "rooms")
        room_status_expr = _room_status_expression(room_columns)
        occupied_expr = "COALESCE(is_occupied, false)" if "is_occupied" in room_columns else "false"
        active_filter = "AND (is_active IS NULL OR is_active = TRUE)" if "is_active" in room_columns else ""
        room_row = db.execute(
            text(
                f"""
                SELECT
                  COALESCE({room_status_expr}, 'unknown') AS room_status,
                  {occupied_expr} AS is_occupied
                FROM rooms
                WHERE property_code = :property_code
                  AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
                  {active_filter}
                LIMIT 1
                """
            ),
            {"property_code": property_code, "room_number": payload.room_number},
        ).mappings().first()

        if not room_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room {payload.room_number} was not found for property {property_code}.",
            )

        room_status = str(room_row["room_status"] or "unknown").lower()
        blocked_reason = None
        if bool(room_row["is_occupied"]):
            blocked_reason = "occupied"
        elif not _is_assignable_room_status(room_status):
            blocked_reason = room_status

        if blocked_reason:
            record_pms_audit_log(
                db,
                property_code=property_code,
                user_email=actor["email"],
                module="frontdesk",
                action="room_assignment_blocked",
                record_type="room",
                record_id=payload.room_number,
                new_value={
                    "booking_id": payload.booking_id,
                    "room_number": payload.room_number,
                    "room_status": room_status,
                    "is_occupied": bool(room_row["is_occupied"]),
                    "reason": blocked_reason,
                },
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Room {payload.room_number} cannot be assigned because its status is "
                    f"{blocked_reason}. Select a clean, inspected, or available room."
                ),
            )

        stmt = text(
            """
            UPDATE bookings
            SET
                room_number = :room_number
            WHERE id = :booking_id
              AND property_code = :property_code
            RETURNING
                id,
                hotel_id,
                guest_name,
                check_in_date,
                check_out_date,
                booking_status,
                property_code,
                room_number
            """
        )

        result = db.execute(
            stmt,
            {
                "room_number": payload.room_number,
                "booking_id": payload.booking_id,
                "property_code": property_code,
            },
        )

        row = result.fetchone()

        if row is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking {payload.booking_id} not found for property {property_code}",
            )

        record_audit_log(
            db,
            action="room_assigned",
            entity_type="booking",
            entity_id=row.id,
            hotel_id=row.hotel_id,
            property_code=row.property_code,
            business_date=row.check_in_date,
            details={"room_number": row.room_number},
        )
        record_pms_audit_log(
            db,
            property_code=row.property_code,
            user_email=actor["email"],
            module="frontdesk",
            action="room_assigned",
            record_type="booking",
            record_id=row.id,
            new_value={
                "room_number": row.room_number,
                "booking_status": row.booking_status,
                "room_status": room_status,
                "check_in_required": True,
            },
        )
        db.commit()

        # SQLAlchemy Row supports attribute-style access with the column names
        return BookingResponse(
            id=row.id,
            guest_name=row.guest_name,
            check_in_date=row.check_in_date.isoformat(),
            check_out_date=row.check_out_date.isoformat(),
            booking_status=row.booking_status,
            property_code=row.property_code,
            room_number=row.room_number,
        )

    except HTTPException:
        # already built a proper error response
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning room: {e}",
        )
