from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.audit_log_service import record_audit_log
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission


router = APIRouter(prefix="/frontdesk", tags=["frontdesk-guest-service"])

RecordType = Literal["guest_message", "trace", "wake_up_call", "task_history"]
RecordStatus = Literal["open", "in_progress", "completed", "cancelled"]
RecordPriority = Literal["low", "normal", "high", "urgent"]

DISPLAY_STATUS = {
    "open": "Open",
    "in_progress": "In Progress",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


class FrontDeskServiceRecordCreate(BaseModel):
    record_type: RecordType
    property_code: str
    booking_id: int | None = None
    reservation_reference: str | None = None
    guest_name: str | None = None
    room_number: str | None = None
    status: RecordStatus = "open"
    priority: RecordPriority = "normal"
    assigned_to: str | None = None
    notes: str | None = None
    task_key: str | None = Field(default=None, max_length=120)
    title: str | None = None
    scheduled_for: datetime | None = None


class FrontDeskServiceRecordUpdate(BaseModel):
    status: RecordStatus | None = None
    priority: RecordPriority | None = None
    assigned_to: str | None = None
    notes: str | None = None
    room_number: str | None = None
    scheduled_for: datetime | None = None


class FrontDeskServiceRecordResponse(BaseModel):
    id: int
    record_type: str
    property_code: str
    booking_id: int | None = None
    reservation_reference: str | None = None
    guest_name: str | None = None
    room_number: str | None = None
    status: str
    status_label: str
    priority: str
    assigned_to: str | None = None
    created_by: str
    created_at: datetime
    completed_at: datetime | None = None
    notes: str | None = None
    task_key: str | None = None
    title: str | None = None
    scheduled_for: datetime | None = None
    updated_at: datetime | None = None


def ensure_frontdesk_service_records_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS frontdesk_service_records (
                id SERIAL PRIMARY KEY,
                record_type VARCHAR(40) NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                booking_id INTEGER NULL,
                reservation_reference VARCHAR(120) NULL,
                guest_name VARCHAR(180) NULL,
                room_number VARCHAR(50) NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'open',
                priority VARCHAR(40) NOT NULL DEFAULT 'normal',
                assigned_to VARCHAR(150) NULL,
                created_by VARCHAR(150) NOT NULL DEFAULT 'frontdesk',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                completed_at TIMESTAMPTZ NULL,
                notes TEXT NULL,
                task_key VARCHAR(120) NULL,
                title VARCHAR(180) NULL,
                scheduled_for TIMESTAMPTZ NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_frontdesk_service_records_property_type_status
            ON frontdesk_service_records (property_code, record_type, status)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_frontdesk_service_records_booking
            ON frontdesk_service_records (property_code, booking_id)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_frontdesk_service_records_task_key
            ON frontdesk_service_records (property_code, record_type, booking_id, task_key)
            WHERE task_key IS NOT NULL
            """
        )
    )


def _normalize_property(property_code: str) -> str:
    value = str(property_code or "").strip().upper()
    if not value:
        raise HTTPException(status_code=400, detail="property_code is required.")
    return value


def _row_to_response(row) -> FrontDeskServiceRecordResponse:
    item = dict(row._mapping if hasattr(row, "_mapping") else row)
    item["status_label"] = DISPLAY_STATUS.get(str(item["status"]).lower(), str(item["status"]).title())
    return FrontDeskServiceRecordResponse(**item)


def _service_permission(record_type: str) -> str:
    if record_type == "wake_up_call":
        return "frontdesk.check_in"
    return "frontdesk.open_folio"


def _fetch_record(db: Session, record_id: int, property_code: str):
    row = db.execute(
        text(
            """
            SELECT *
            FROM frontdesk_service_records
            WHERE id = :record_id
              AND property_code = :property_code
            """
        ),
        {"record_id": record_id, "property_code": property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Front Desk service record not found for selected property.")
    return row


@router.get("/service-records", response_model=list[FrontDeskServiceRecordResponse])
def list_frontdesk_service_records(
    property_code: str = Query(...),
    record_type: RecordType | None = Query(None),
    status_filter: RecordStatus | None = Query(None, alias="status"),
    booking_id: int | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property(property_code)
    require_pms_permission(
        db,
        permission_key="frontdesk.open_folio",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    ensure_frontdesk_service_records_table(db)
    clauses = ["property_code = :property_code"]
    params: dict[str, object] = {"property_code": property_code}
    if record_type:
        clauses.append("record_type = :record_type")
        params["record_type"] = record_type
    if status_filter:
        clauses.append("status = :status")
        params["status"] = status_filter
    if booking_id is not None:
        clauses.append("booking_id = :booking_id")
        params["booking_id"] = booking_id
    rows = db.execute(
        text(
            f"""
            SELECT *
            FROM frontdesk_service_records
            WHERE {" AND ".join(clauses)}
            ORDER BY
              CASE status
                WHEN 'open' THEN 1
                WHEN 'in_progress' THEN 2
                WHEN 'completed' THEN 3
                WHEN 'cancelled' THEN 4
                ELSE 5
              END,
              COALESCE(scheduled_for, created_at) ASC,
              id DESC
            LIMIT 300
            """
        ),
        params,
    ).mappings().all()
    db.commit()
    return [_row_to_response(row) for row in rows]


@router.post(
    "/service-records",
    response_model=FrontDeskServiceRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_frontdesk_service_record(
    payload: FrontDeskServiceRecordCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key=_service_permission(payload.record_type),
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    ensure_frontdesk_service_records_table(db)

    if payload.task_key and payload.booking_id is not None:
        existing = db.execute(
            text(
                """
                SELECT *
                FROM frontdesk_service_records
                WHERE property_code = :property_code
                  AND record_type = :record_type
                  AND booking_id = :booking_id
                  AND task_key = :task_key
                LIMIT 1
                """
            ),
            {
                "property_code": property_code,
                "record_type": payload.record_type,
                "booking_id": payload.booking_id,
                "task_key": payload.task_key,
            },
        ).mappings().first()
        if existing:
            return _update_record_status(
                db=db,
                record_id=int(existing["id"]),
                property_code=property_code,
                actor_email=actor["email"],
                payload=FrontDeskServiceRecordUpdate(
                    status=payload.status,
                    priority=payload.priority,
                    assigned_to=payload.assigned_to,
                    notes=payload.notes,
                    room_number=payload.room_number,
                    scheduled_for=payload.scheduled_for,
                ),
            )

    row = db.execute(
        text(
            """
            INSERT INTO frontdesk_service_records (
                record_type, property_code, booking_id, reservation_reference,
                guest_name, room_number, status, priority, assigned_to,
                created_by, completed_at, notes, task_key, title, scheduled_for
            )
            VALUES (
                :record_type, :property_code, :booking_id, :reservation_reference,
                :guest_name, :room_number, :status, :priority, :assigned_to,
                :created_by,
                CASE WHEN :status IN ('completed', 'cancelled') THEN now() ELSE NULL END,
                :notes, :task_key, :title, :scheduled_for
            )
            RETURNING *
            """
        ),
        {
            "record_type": payload.record_type,
            "property_code": property_code,
            "booking_id": payload.booking_id,
            "reservation_reference": payload.reservation_reference,
            "guest_name": payload.guest_name,
            "room_number": payload.room_number,
            "status": payload.status,
            "priority": payload.priority,
            "assigned_to": payload.assigned_to,
            "created_by": actor["email"],
            "notes": payload.notes,
            "task_key": payload.task_key,
            "title": payload.title,
            "scheduled_for": payload.scheduled_for,
        },
    ).mappings().first()
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="frontdesk_service_record_created",
        record_type=payload.record_type,
        record_id=row["id"],
        new_value=dict(row),
    )
    record_audit_log(
        db,
        action="frontdesk_service_record_created",
        entity_type=payload.record_type,
        entity_id=int(row["id"]),
        property_code=property_code,
        performed_by=actor["email"],
        details={"booking_id": payload.booking_id, "status": payload.status, "task_key": payload.task_key},
    )
    db.commit()
    return _row_to_response(row)


def _update_record_status(
    *,
    db: Session,
    record_id: int,
    property_code: str,
    actor_email: str,
    payload: FrontDeskServiceRecordUpdate,
) -> FrontDeskServiceRecordResponse:
    old_row = _fetch_record(db, record_id, property_code)
    next_status = payload.status or old_row["status"]
    row = db.execute(
        text(
            """
            UPDATE frontdesk_service_records
            SET
              status = :status,
              priority = COALESCE(:priority, priority),
              assigned_to = COALESCE(:assigned_to, assigned_to),
              notes = COALESCE(:notes, notes),
              room_number = COALESCE(:room_number, room_number),
              scheduled_for = COALESCE(:scheduled_for, scheduled_for),
              completed_at = CASE
                WHEN :status IN ('completed', 'cancelled') THEN COALESCE(completed_at, now())
                WHEN :status IN ('open', 'in_progress') THEN NULL
                ELSE completed_at
              END,
              updated_at = now()
            WHERE id = :record_id
              AND property_code = :property_code
            RETURNING *
            """
        ),
        {
            "record_id": record_id,
            "property_code": property_code,
            "status": next_status,
            "priority": payload.priority,
            "assigned_to": payload.assigned_to,
            "notes": payload.notes,
            "room_number": payload.room_number,
            "scheduled_for": payload.scheduled_for,
        },
    ).mappings().first()
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor_email,
        module="frontdesk",
        action="frontdesk_service_record_status_updated",
        record_type=str(row["record_type"]),
        record_id=record_id,
        old_value={"status": old_row["status"], "priority": old_row["priority"]},
        new_value=dict(row),
    )
    record_audit_log(
        db,
        action="frontdesk_service_record_status_updated",
        entity_type=str(row["record_type"]),
        entity_id=record_id,
        property_code=property_code,
        performed_by=actor_email,
        details={"old_status": old_row["status"], "new_status": row["status"], "booking_id": row["booking_id"]},
    )
    db.commit()
    return _row_to_response(row)


@router.patch("/service-records/{record_id}", response_model=FrontDeskServiceRecordResponse)
def update_frontdesk_service_record(
    record_id: int,
    payload: FrontDeskServiceRecordUpdate,
    property_code: str = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property(property_code)
    ensure_frontdesk_service_records_table(db)
    old_row = _fetch_record(db, record_id, property_code)
    actor = require_pms_permission(
        db,
        permission_key=_service_permission(str(old_row["record_type"])),
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    return _update_record_status(
        db=db,
        record_id=record_id,
        property_code=property_code,
        actor_email=actor["email"],
        payload=payload,
    )
