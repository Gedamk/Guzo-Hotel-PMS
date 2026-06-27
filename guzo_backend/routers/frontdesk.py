# guzo_backend/routers/frontdesk.py
import re
from datetime import datetime, date, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.postgres_db import get_db
from ..api.rooms_housekeeping_api import _set_housekeeping_status
from ..services.audit_log_service import record_audit_log
from ..services.business_date_lock_service import assert_business_date_editable
from ..services.guest_profile_service import (
    find_or_create_guest_profile,
    link_guest_profile_to_booking,
    queue_guest_notification,
)
from ..services.pms_security_service import record_pms_audit_log, require_pms_permission, require_property_access
from ..services.payment_lifecycle_service import transfer_deposit_to_folio

router = APIRouter(prefix="/frontdesk", tags=["frontdesk"])


class FrontdeskBooking(BaseModel):
    id: int
    confirmation_id: Optional[str] = None
    guest_name: str
    guest_email: Optional[str] = None
    check_in_date: date
    check_out_date: date
    booking_status: str
    property_code: str
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    rate_per_night_etb: Optional[float] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    channel: Optional[str] = None
    balance_due: Optional[float] = None
    guarantee_status: Optional[str] = None
    housekeeping_status: Optional[str] = None
    special_requests: Optional[str] = None
    q_status: Optional[str] = None
    q_started_at: Optional[datetime] = None
    q_priority: Optional[str] = None
    q_notes: Optional[str] = None
    q_removed_at: Optional[datetime] = None
    q_removed_by: Optional[str] = None
    registration_card_generated_at: Optional[datetime] = None
    registration_card_generated_by: Optional[str] = None
    registration_card_signed: Optional[bool] = None
    registration_card_signed_at: Optional[datetime] = None
    registration_card_notes: Optional[str] = None
    authorization_status: Optional[str] = None
    authorization_amount: Optional[float] = None
    authorization_type: Optional[str] = None
    authorization_code: Optional[str] = None
    authorization_notes: Optional[str] = None
    authorization_recorded_by: Optional[str] = None
    authorization_recorded_at: Optional[datetime] = None
    upsell_offered: Optional[bool] = None
    upsell_accepted: Optional[bool] = None
    upsell_declined: Optional[bool] = None
    upsell_from_room_type: Optional[str] = None
    upsell_to_room_type: Optional[str] = None
    upsell_amount_per_night: Optional[float] = None
    upsell_total_amount: Optional[float] = None
    upsell_recorded_by: Optional[str] = None
    upsell_recorded_at: Optional[datetime] = None


class FrontdeskActionRequest(BaseModel):
    booking_id: int
    property_code: str
    business_date: Optional[date] = None
    manager_override: bool = False
    override_reason: Optional[str] = None


class ReservationWorkflowActionRequest(FrontdeskActionRequest):
    action: str
    note: Optional[str] = None
    amount: Optional[float] = None


class FrontdeskStayActionRequest(FrontdeskActionRequest):
    room_number: Optional[str] = None
    check_out_date: Optional[date] = None
    note: Optional[str] = None


class FrontdeskQRequest(FrontdeskActionRequest):
    q_priority: Optional[str] = "normal"
    q_notes: Optional[str] = None


class FrontdeskRegistrationCardRequest(FrontdeskActionRequest):
    signed: bool = False
    notes: Optional[str] = None


class FrontdeskManualAuthorizationRequest(FrontdeskActionRequest):
    authorization_amount: float
    authorization_type: Optional[str] = "offline"
    authorization_code: Optional[str] = None
    authorization_notes: Optional[str] = None


class FrontdeskUpsellRequest(FrontdeskActionRequest):
    offered: bool = True
    accepted: bool = False
    declined: bool = False
    from_room_type: Optional[str] = None
    to_room_type: Optional[str] = None
    amount_per_night: Optional[float] = None
    total_amount: Optional[float] = None
    notes: Optional[str] = None


def _parse_business_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format, expected YYYY-MM-DD",
        )


def _booking_columns(db: Session) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'bookings'
            """
        )
    ).fetchall()
    return {row[0] for row in rows}


def _column_or_null(columns: set[str], column_name: str, column_type: str = "text") -> str:
    if column_name in columns:
        return f"b.{column_name}"
    return f"NULL::{column_type}"


def _amount_expression(columns: set[str]) -> str:
    available = [
        f"b.{column}"
        for column in ("total_amount", "total_amount_etb", "total_revenue_etb")
        if column in columns
    ]
    if not available:
        return "NULL::numeric"
    return f"COALESCE({', '.join(available)})"


def _payment_status_expression(columns: set[str]) -> str:
    if "payment_status" in columns:
        return "COALESCE(b.payment_status, 'pending')"
    return "'pending'::text"


def _currency_from_notes(notes: str | None) -> str | None:
    match = re.search(r"Currency:\s*([A-Za-z]{3})", str(notes or ""), re.IGNORECASE)
    return match.group(1).upper() if match else None


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema = current_schema()
                    AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _ensure_frontdesk_workflow_columns(db: Session) -> None:
    statements = [
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_status VARCHAR(40)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_started_at TIMESTAMP",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_priority VARCHAR(40)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_notes TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_removed_at TIMESTAMP",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_removed_by VARCHAR(150)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_generated_at TIMESTAMP",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_generated_by VARCHAR(150)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_signed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_signed_at TIMESTAMP",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_notes TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_status VARCHAR(50)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_amount NUMERIC(12, 2)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_type VARCHAR(50)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_code VARCHAR(120)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_notes TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_recorded_by VARCHAR(150)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_recorded_at TIMESTAMP",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_offered BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_accepted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_declined BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_from_room_type VARCHAR(100)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_to_room_type VARCHAR(100)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_amount_per_night NUMERIC(12, 2)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_total_amount NUMERIC(12, 2)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_recorded_by VARCHAR(150)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_recorded_at TIMESTAMP",
    ]
    for statement in statements:
        db.execute(text(statement))


def _room_status_expression(columns: set[str]) -> str:
    if "hk_status" in columns:
        return "r.hk_status"
    if "housekeeping_status" in columns:
        return "r.housekeeping_status"
    if "status" in columns:
        return "r.status"
    return "'unknown'"


def _room_readiness(db: Session, property_code: str, room_number: str) -> dict[str, Any]:
    if not _table_exists(db, "rooms"):
        return {
            "exists": False,
            "is_occupied": True,
            "status": "unknown",
            "ready_for_checkin": False,
            "assignable": False,
        }

    columns = _table_columns(db, "rooms")
    status_expr = _room_status_expression(columns)
    occupied_expr = "COALESCE(r.is_occupied, false)" if "is_occupied" in columns else "false"
    active_filter = "AND (r.is_active IS NULL OR r.is_active = TRUE)" if "is_active" in columns else ""

    row = db.execute(
        text(
            f"""
            SELECT
              COALESCE({status_expr}, 'unknown') AS room_status,
              {occupied_expr} AS is_occupied
            FROM rooms r
            WHERE r.property_code = :property_code
              AND CAST(r.room_number AS TEXT) = CAST(:room_number AS TEXT)
              {active_filter}
            LIMIT 1
            """
        ),
        {"property_code": property_code, "room_number": room_number},
    ).mappings().first()

    if not row:
        return {
            "exists": False,
            "is_occupied": True,
            "status": "unknown",
            "ready_for_checkin": False,
            "assignable": False,
        }

    status = str(row["room_status"] or "unknown").lower()
    is_occupied = bool(row["is_occupied"])
    out_of_order = (
        "out" in status
        or "ooo" in status
        or "order" in status
        or "maintenance" in status
        or "service" in status
    )
    inspected = "inspected" in status
    clean = "clean" in status
    ready = not is_occupied and not out_of_order and inspected
    return {
        "exists": True,
        "is_occupied": is_occupied,
        "status": status,
        "ready_for_checkin": ready,
        "clean_but_uninspected": not is_occupied and not out_of_order and clean and not inspected,
        "assignable": not is_occupied and not out_of_order,
    }


def _select_frontdesk_booking_sql(columns: set[str]):
    return text(
        f"""
        SELECT
            b.id,
            {_column_or_null(columns, "confirmation_id")} AS confirmation_id,
            b.guest_name,
            {_column_or_null(columns, "guest_email")} AS guest_email,
            b.check_in_date,
            b.check_out_date,
            b.booking_status,
            b.property_code,
            {_column_or_null(columns, "room_number")} AS room_number,
            {_column_or_null(columns, "room_type")} AS room_type,
            {_amount_expression(columns)} AS total_amount,
            {_column_or_null(columns, "rate_per_night_etb", "numeric")} AS rate_per_night_etb,
            {_column_or_null(columns, "payment_method")} AS payment_method,
            {_payment_status_expression(columns)} AS payment_status,
            {_column_or_null(columns, "currency")} AS currency,
            {_column_or_null(columns, "notes")} AS notes,
            {_column_or_null(columns, "source")} AS source,
            {_column_or_null(columns, "q_status")} AS q_status,
            {_column_or_null(columns, "q_started_at", "timestamp")} AS q_started_at,
            {_column_or_null(columns, "q_priority")} AS q_priority,
            {_column_or_null(columns, "q_notes")} AS q_notes,
            {_column_or_null(columns, "q_removed_at", "timestamp")} AS q_removed_at,
            {_column_or_null(columns, "q_removed_by")} AS q_removed_by,
            {_column_or_null(columns, "registration_card_generated_at", "timestamp")} AS registration_card_generated_at,
            {_column_or_null(columns, "registration_card_generated_by")} AS registration_card_generated_by,
            {_column_or_null(columns, "registration_card_signed", "boolean")} AS registration_card_signed,
            {_column_or_null(columns, "registration_card_signed_at", "timestamp")} AS registration_card_signed_at,
            {_column_or_null(columns, "registration_card_notes")} AS registration_card_notes,
            {_column_or_null(columns, "authorization_status")} AS authorization_status,
            {_column_or_null(columns, "authorization_amount", "numeric")} AS authorization_amount,
            {_column_or_null(columns, "authorization_type")} AS authorization_type,
            {_column_or_null(columns, "authorization_code")} AS authorization_code,
            {_column_or_null(columns, "authorization_notes")} AS authorization_notes,
            {_column_or_null(columns, "authorization_recorded_by")} AS authorization_recorded_by,
            {_column_or_null(columns, "authorization_recorded_at", "timestamp")} AS authorization_recorded_at,
            {_column_or_null(columns, "upsell_offered", "boolean")} AS upsell_offered,
            {_column_or_null(columns, "upsell_accepted", "boolean")} AS upsell_accepted,
            {_column_or_null(columns, "upsell_declined", "boolean")} AS upsell_declined,
            {_column_or_null(columns, "upsell_from_room_type")} AS upsell_from_room_type,
            {_column_or_null(columns, "upsell_to_room_type")} AS upsell_to_room_type,
            {_column_or_null(columns, "upsell_amount_per_night", "numeric")} AS upsell_amount_per_night,
            {_column_or_null(columns, "upsell_total_amount", "numeric")} AS upsell_total_amount,
            {_column_or_null(columns, "upsell_recorded_by")} AS upsell_recorded_by,
            {_column_or_null(columns, "upsell_recorded_at", "timestamp")} AS upsell_recorded_at,
            COALESCE(
                {_column_or_null(columns, "channel")},
                {_column_or_null(columns, "source")}
            ) AS channel
        FROM bookings b
        WHERE b.id = :id
          AND b.property_code = :property_code
        """
    )


def _frontdesk_booking_payload(db: Session, row) -> dict[str, Any]:
    item = dict(row._mapping)
    property_code = str(item.get("property_code") or "").strip().upper()
    booking_id = int(item["id"])
    room_number = str(item.get("room_number") or "").strip()

    balance_due = float(item.get("total_amount") or 0)
    if _table_exists(db, "folios"):
        folio_row = db.execute(
            text(
                """
                SELECT COALESCE(balance, 0) AS balance
                FROM folios
                WHERE property_code = :property_code
                  AND booking_id = :booking_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_code": property_code, "booking_id": booking_id},
        ).mappings().first()
        if folio_row:
            balance_due = float(folio_row["balance"] or 0)

    housekeeping_status = None
    if room_number and _table_exists(db, "housekeeping_status"):
        hk_columns = _table_columns(db, "housekeeping_status")
        hk_order_parts = []
        if "business_date" in hk_columns:
            hk_order_parts.append("business_date DESC")
        if "updated_at" in hk_columns:
            hk_order_parts.append("updated_at DESC NULLS LAST")
        if "created_at" in hk_columns:
            hk_order_parts.append("created_at DESC NULLS LAST")
        if "id" in hk_columns:
            hk_order_parts.append("id DESC")
        hk_order = ", ".join(hk_order_parts) or "room_number"
        hk_row = db.execute(
            text(
                f"""
                SELECT hk_status
                FROM housekeeping_status
                WHERE property_code = :property_code
                  AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
                ORDER BY {hk_order}
                LIMIT 1
                """
            ),
            {"property_code": property_code, "room_number": room_number},
        ).mappings().first()
        if hk_row:
            housekeeping_status = hk_row["hk_status"]

    item["balance_due"] = balance_due
    item["currency"] = _currency_from_notes(item.get("notes")) or str(item.get("currency") or "ETB").upper()
    item["guarantee_status"] = item.get("payment_status") or "pending"
    item["housekeeping_status"] = housekeeping_status
    item["special_requests"] = item.get("notes")
    return item


def _folio_row(db: Session, property_code: str, booking_id: int):
    if not _table_exists(db, "folios"):
        return None
    return db.execute(
        text(
            """
            SELECT id,
                   COALESCE(balance, 0) AS balance,
                   COALESCE(status, 'open') AS status,
                   COALESCE(currency, 'ETB') AS currency
            FROM folios
            WHERE property_code = :property_code
              AND booking_id = :booking_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).mappings().first()


def _ensure_guest_notification_outbox(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER,
                property_code VARCHAR(50) NOT NULL,
                channel VARCHAR(50) NOT NULL,
                recipient TEXT NULL,
                action VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                business_date DATE NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'queued',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER"))
    db.execute(text("ALTER TABLE guest_notification_outbox ALTER COLUMN booking_id DROP NOT NULL"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ"))


def _queue_guest_feedback_request(
    db: Session,
    *,
    row,
    booking_id: int,
    property_code: str,
    business_date: date,
) -> str:
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=row.guest_name,
        email=getattr(row, "guest_email", None),
        notes=getattr(row, "notes", None),
    )
    link_guest_profile_to_booking(db, booking_id=booking_id, guest_profile=guest_profile)
    message = (
        f"Dear {row.guest_name}, thank you for staying with us. "
        "We would appreciate your feedback about your visit so our team can continue improving your experience."
    )
    return queue_guest_notification(
        db,
        property_code=property_code,
        booking_id=booking_id,
        guest_profile=guest_profile,
        guest_email=getattr(row, "guest_email", None),
        action="guest_feedback_request",
        message=message,
        business_date=business_date,
    )


def _append_booking_note(
    db: Session,
    *,
    columns: set[str],
    booking_id: int,
    property_code: str,
    note: str,
) -> None:
    if "notes" not in columns:
        return
    db.execute(
        text(
            """
            UPDATE bookings
            SET notes = NULLIF(CONCAT_WS(E'\n', NULLIF(notes, ''), :note), '')
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {"booking_id": booking_id, "property_code": property_code, "note": note},
    )


def _append_note_update(columns: set[str], updates: list[str], params: dict[str, Any], note: str):
    if "notes" not in columns:
        return
    updates.append(
        """
        notes = NULLIF(
            CONCAT_WS(E'\n', NULLIF(notes, ''), :workflow_note),
            ''
        )
        """
    )
    params["workflow_note"] = note


def _require_frontdesk_workflow_booking(
    db: Session,
    *,
    booking_id: int,
    property_code: str,
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    normalized_property = property_code.strip().upper()
    row = db.execute(
        select_sql,
        {"id": booking_id, "property_code": normalized_property},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    return columns, select_sql, normalized_property, row


def _update_booking_workflow_fields(
    db: Session,
    *,
    booking_id: int,
    property_code: str,
    fields: dict[str, Any],
) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{field} = :{field}" for field in fields)
    params = {"booking_id": booking_id, "property_code": property_code, **fields}
    db.execute(
        text(
            f"""
            UPDATE bookings
            SET {assignments}
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        params,
    )


def _audit_check_in_blocked(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    booking_id: int,
    reason: str,
    row,
) -> None:
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor_email,
        module="frontdesk",
        action="check_in_blocked_by_readiness",
        record_type="booking",
        record_id=booking_id,
        old_value={"booking_status": getattr(row, "booking_status", None)},
        new_value={"blocked_reason": reason},
    )
    db.commit()


def _record_reservation_trace(
    db: Session,
    *,
    booking_id: int,
    property_code: str,
    action: str,
    note: str,
    business_date: Optional[date],
):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reservation_traces (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER NOT NULL,
                property_code VARCHAR(50) NOT NULL,
                action VARCHAR(100) NOT NULL,
                note TEXT NOT NULL,
                due_date DATE NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                owner VARCHAR(100) NOT NULL DEFAULT 'Reservations',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER"))
    db.execute(text("ALTER TABLE guest_notification_outbox ALTER COLUMN booking_id DROP NOT NULL"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ"))
    db.execute(text("UPDATE guest_notification_outbox SET attempt_count = COALESCE(attempt_count, 0)"))
    db.execute(
        text(
            """
            INSERT INTO reservation_traces (
                booking_id,
                property_code,
                action,
                note,
                due_date
            )
            VALUES (
                :booking_id,
                :property_code,
                :action,
                :note,
                :due_date
            )
            """
        ),
        {
            "booking_id": booking_id,
            "property_code": property_code,
            "action": action,
            "note": note,
            "due_date": business_date,
        },
    )


def _record_frontdesk_alert(
    db: Session,
    *,
    booking_id: int,
    property_code: str,
    alert_type: str,
    message: str,
    business_date: Optional[date],
):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS frontdesk_alerts (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER NOT NULL,
                property_code VARCHAR(50) NOT NULL,
                alert_type VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                business_date DATE NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO frontdesk_alerts (
                booking_id,
                property_code,
                alert_type,
                message,
                business_date
            )
            VALUES (
                :booking_id,
                :property_code,
                :alert_type,
                :message,
                :business_date
            )
            """
        ),
        {
            "booking_id": booking_id,
            "property_code": property_code,
            "alert_type": alert_type,
            "message": message,
            "business_date": business_date,
        },
    )


def _infer_guest_notification_channel(row, action: str) -> tuple[str, Optional[str]]:
    source = str(row.source or row.channel or "").lower()
    notes = str(row.notes or "")
    email = getattr(row, "guest_email", None)

    if email:
        return "email", email

    telegram_match = re.search(r"Telegram Chat ID:\s*([0-9-]+)", notes, re.IGNORECASE)
    if "telegram" in source and telegram_match:
        return "telegram", telegram_match.group(1)

    if "telegram" in source:
        return "telegram", None
    if "chatbot" in source or "website" in source or "online" in source:
        return "chatbot", None

    return "frontdesk_followup", None


def _record_guest_notification(
    db: Session,
    *,
    row,
    booking_id: int,
    property_code: str,
    action: str,
    message: str,
    business_date: Optional[date],
):
    channel, recipient = _infer_guest_notification_channel(row, action)
    status = "queued" if recipient else "pending_contact_review"
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER NOT NULL,
                property_code VARCHAR(50) NOT NULL,
                channel VARCHAR(50) NOT NULL,
                recipient TEXT NULL,
                action VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                business_date DATE NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'queued',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO guest_notification_outbox (
                booking_id,
                property_code,
                channel,
                recipient,
                action,
                message,
                business_date,
                status
            )
            VALUES (
                :booking_id,
                :property_code,
                :channel,
                :recipient,
                :action,
                :message,
                :business_date,
                :status
            )
            """
        ),
        {
            "booking_id": booking_id,
            "property_code": property_code,
            "channel": channel,
            "recipient": recipient,
            "action": action,
            "message": message,
            "business_date": business_date,
            "status": status,
        },
    )


@router.get("/bookings", response_model=List[FrontdeskBooking])
def get_frontdesk_bookings(
    date: str = Query(..., description="Business date in YYYY-MM-DD format"),
    scope: str = Query("today", pattern="^(today|touches)$"),
    property: str = Query(
        ...,
        alias="property",
        min_length=1,
        description="Required hotel property code (for example DRE001)",
    ),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    business_date = _parse_business_date(date)
    property_code = property.strip().upper()
    try:
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    except HTTPException as exc:
        if exc.status_code == 404:
            return []
        raise
    columns = _booking_columns(db)

    where_clauses = [
        "b.check_in_date <= :bd",
        "b.check_out_date >= :bd",
    ]
    params = {"bd": business_date}

    where_clauses.append("b.property_code = :pc")
    params["pc"] = property_code

    where_sql = " AND ".join(where_clauses)

    sql = text(
        f"""
        SELECT
            b.id,
            {_column_or_null(columns, "confirmation_id")} AS confirmation_id,
            b.guest_name,
            {_column_or_null(columns, "guest_email")} AS guest_email,
            b.check_in_date,
            b.check_out_date,
            b.booking_status,
            b.property_code,
            {_column_or_null(columns, "room_number")} AS room_number,
            {_column_or_null(columns, "room_type")} AS room_type,
            {_amount_expression(columns)} AS total_amount,
            {_column_or_null(columns, "rate_per_night_etb", "numeric")} AS rate_per_night_etb,
            {_column_or_null(columns, "payment_method")} AS payment_method,
            {_payment_status_expression(columns)} AS payment_status,
            {_column_or_null(columns, "currency")} AS currency,
            {_column_or_null(columns, "notes")} AS notes,
            {_column_or_null(columns, "source")} AS source,
            COALESCE(
                {_column_or_null(columns, "channel")},
                {_column_or_null(columns, "source")}
            ) AS channel
        FROM bookings b
        WHERE {where_sql}
        ORDER BY b.check_in_date, b.guest_name
        """
    )

    rows = db.execute(sql, params).fetchall()
    return [_frontdesk_booking_payload(db, row) for row in rows]


@router.post("/reservation-action", response_model=FrontdeskBooking)
def apply_reservation_workflow_action(
    payload: ReservationWorkflowActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    property_code = payload.property_code.strip().upper()
    action = payload.action.strip().lower()
    require_pms_permission(
        db,
        permission_key="reservations.modify_booking",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    select_sql = _select_frontdesk_booking_sql(columns)

    row = db.execute(
        select_sql,
        {"id": payload.booking_id, "property_code": property_code},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")

    action_labels = {
        "open_reservation": "Reservation opened for full review.",
        "review_guarantee": "Guarantee review started by Reservations.",
        "send_deposit_link": "Deposit request sent to guest.",
        "record_deposit": "Deposit recorded and reservation confirmed.",
        "request_card_guarantee": "Card guarantee request sent to guest.",
        "approve_pay_at_hotel": "Pay-at-hotel approved; Front Desk must collect payment at check-in.",
        "mark_guaranteed": "Reservation marked guaranteed.",
        "waive_guarantee": "Guarantee waived by manager approval.",
        "add_trace": "Reservation trace created for follow-up.",
        "cancel_by_deadline": "Reservation cancelled because guarantee deadline was not met.",
        "hold_at_frontdesk": "Reservation held at Front Desk pending guarantee review.",
        "send_to_frontdesk": "Reservation sent to Front Desk for arrival processing.",
        "add_alert": "Front Desk alert added to reservation.",
        "send_confirmation": "Reservation confirmation sent/logged.",
        "add_arrival_note": "Arrival note added for Front Desk.",
        "assign_room_preference": "Room preference recorded for assignment review.",
        "mark_vip": "VIP/special attention note added.",
    }
    if action not in action_labels:
        raise HTTPException(status_code=400, detail=f"Unsupported reservation action: {payload.action}")

    base_note = payload.note.strip() if payload.note else action_labels[action]
    timestamped_note = f"[Reservations SOP] {base_note}"
    updates: list[str] = []
    params: dict[str, Any] = {"id": payload.booking_id, "property_code": property_code}

    if action in {"review_guarantee", "send_deposit_link", "request_card_guarantee", "hold_at_frontdesk"}:
        updates.append("booking_status = 'pending_guarantee'")
        if "payment_status" in columns:
            updates.append("payment_status = 'pending'")

    if action == "record_deposit":
        updates.append("booking_status = 'confirmed'")
        if "payment_status" in columns:
            updates.append("payment_status = 'deposit_paid'")

    if action == "approve_pay_at_hotel":
        updates.append("booking_status = 'confirmed'")
        if "payment_status" in columns:
            updates.append("payment_status = 'pending'")

    if action in {"mark_guaranteed", "send_to_frontdesk"}:
        updates.append("booking_status = 'confirmed'")
        if "payment_status" in columns and action == "mark_guaranteed":
            updates.append("payment_status = 'guaranteed'")

    if action == "waive_guarantee":
        updates.append("booking_status = 'confirmed'")
        if "payment_status" in columns:
            updates.append("payment_status = 'pending'")

    if action == "cancel_by_deadline":
        updates.append("booking_status = 'cancelled'")

    _append_note_update(columns, updates, params, timestamped_note)

    if updates:
        db.execute(
            text(
                f"""
                UPDATE bookings
                SET {', '.join(updates)}
                WHERE id = :id
                  AND property_code = :property_code
                """
            ),
            params,
        )

    trace_actions = {
        "review_guarantee",
        "send_deposit_link",
        "request_card_guarantee",
        "add_trace",
        "cancel_by_deadline",
        "send_confirmation",
    }
    if action in trace_actions:
        _record_reservation_trace(
            db,
            booking_id=payload.booking_id,
            property_code=property_code,
            action=action,
            note=base_note,
            business_date=payload.business_date,
        )

    alert_messages = {
        "approve_pay_at_hotel": "Payment pending. Collect payment at check-in.",
        "waive_guarantee": "Manager waived guarantee. Verify payment instructions at check-in.",
        "hold_at_frontdesk": "Check-in hold: guarantee review required before key issue.",
        "send_to_frontdesk": "Reservation cleared by Reservations for Front Desk arrival handling.",
        "add_alert": base_note,
        "add_arrival_note": base_note,
        "mark_vip": "VIP/special attention requested by Reservations.",
    }
    if action in alert_messages:
        _record_frontdesk_alert(
            db,
            booking_id=payload.booking_id,
            property_code=property_code,
            alert_type=action,
            message=alert_messages[action],
            business_date=payload.business_date,
        )

    guest_messages = {
        "send_deposit_link": (
            f"Dear {row.guest_name}, thank you for choosing our hotel. "
            "To secure your reservation, please complete the deposit request sent by our Reservations team. "
            "Our team remains at your service for any assistance."
        ),
        "request_card_guarantee": (
            f"Dear {row.guest_name}, thank you for your reservation. "
            "To guarantee your stay, our Reservations team will assist you with a secure card guarantee request."
        ),
        "approve_pay_at_hotel": (
            f"Dear {row.guest_name}, your reservation has been approved for payment at the hotel. "
            "For a smooth arrival, please be prepared to settle the required payment at check-in."
        ),
        "record_deposit": (
            f"Dear {row.guest_name}, thank you. Your deposit has been recorded and your reservation is confirmed. "
            "We look forward to welcoming you."
        ),
        "mark_guaranteed": (
            f"Dear {row.guest_name}, your reservation is now guaranteed and confirmed. "
            "We look forward to welcoming you."
        ),
        "send_confirmation": (
            f"Dear {row.guest_name}, your reservation is confirmed. "
            f"Confirmation Number: {row.confirmation_id or f'Booking #{payload.booking_id}'}. "
            f"Stay: {row.check_in_date.isoformat()} to {row.check_out_date.isoformat()}. "
            f"Room Type: {row.room_type or 'TBD'}. "
            "Our Front Desk and Reservations team look forward to welcoming you."
        ),
        "cancel_by_deadline": (
            f"Dear {row.guest_name}, your reservation has been cancelled because the guarantee requirement was not completed by the deadline. "
            "Please contact Reservations if you would like to make a new booking."
        ),
    }
    if action in guest_messages:
        _record_guest_notification(
            db,
            row=row,
            booking_id=payload.booking_id,
            property_code=property_code,
            action=action,
            message=guest_messages[action],
            business_date=payload.business_date,
        )

    record_audit_log(
        db,
        action=f"reservation_{action}",
        entity_type="booking",
        entity_id=payload.booking_id,
        property_code=property_code,
        business_date=payload.business_date,
        performed_by="reservations",
        details={
            "previous_status": row.booking_status,
            "previous_payment_status": row.payment_status,
            "note": base_note,
            "amount": payload.amount,
        },
    )
    db.commit()

    row = db.execute(
        select_sql,
        {"id": payload.booking_id, "property_code": property_code},
    ).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/q/place", response_model=FrontdeskBooking)
def place_reservation_on_q(
    payload: FrontdeskQRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    columns, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    priority = str(payload.q_priority or "normal").strip().lower()
    if priority not in {"normal", "vip", "urgent"}:
        raise HTTPException(status_code=400, detail="Q priority must be normal, VIP, or urgent.")
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "q_status": "waiting",
            "q_started_at": datetime.utcnow(),
            "q_priority": priority,
            "q_notes": payload.q_notes or "Guest waiting for room readiness.",
            "q_removed_at": None,
            "q_removed_by": None,
        },
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Guest placed on Q as {priority}. {payload.q_notes or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="reservation_placed_on_q",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"q_status": getattr(row, "q_status", None)},
        new_value={"q_status": "waiting", "q_priority": priority, "q_notes": payload.q_notes},
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/q/remove", response_model=FrontdeskBooking)
def remove_reservation_from_q(
    payload: FrontdeskQRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    columns, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "q_status": "removed",
            "q_removed_at": datetime.utcnow(),
            "q_removed_by": actor["email"],
            "q_notes": payload.q_notes or getattr(row, "q_notes", None),
        },
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Guest removed from Q. {payload.q_notes or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="reservation_removed_from_q",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"q_status": getattr(row, "q_status", None), "q_priority": getattr(row, "q_priority", None)},
        new_value={"q_status": "removed", "q_removed_by": actor["email"]},
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/q/update", response_model=FrontdeskBooking)
def update_q_priority_or_notes(
    payload: FrontdeskQRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    _, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    priority = str(payload.q_priority or getattr(row, "q_priority", None) or "normal").strip().lower()
    if priority not in {"normal", "vip", "urgent"}:
        raise HTTPException(status_code=400, detail="Q priority must be normal, VIP, or urgent.")
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={"q_priority": priority, "q_notes": payload.q_notes},
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="q_priority_changed",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"q_priority": getattr(row, "q_priority", None), "q_notes": getattr(row, "q_notes", None)},
        new_value={"q_priority": priority, "q_notes": payload.q_notes},
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/registration-card/generated", response_model=FrontdeskBooking)
def mark_registration_card_generated(
    payload: FrontdeskRegistrationCardRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    columns, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "registration_card_generated_at": datetime.utcnow(),
            "registration_card_generated_by": actor["email"],
            "registration_card_notes": payload.notes,
        },
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Registration card generated. {payload.notes or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="registration_card_generated",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"registration_card_generated_at": getattr(row, "registration_card_generated_at", None)},
        new_value={"registration_card_generated_by": actor["email"], "registration_card_notes": payload.notes},
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/registration-card/signed", response_model=FrontdeskBooking)
def mark_registration_card_signed(
    payload: FrontdeskRegistrationCardRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    _, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "registration_card_signed": bool(payload.signed),
            "registration_card_signed_at": datetime.utcnow() if payload.signed else None,
            "registration_card_notes": payload.notes,
        },
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="registration_card_signed" if payload.signed else "registration_card_acknowledgement_removed",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"registration_card_signed": getattr(row, "registration_card_signed", None)},
        new_value={"registration_card_signed": payload.signed, "registration_card_notes": payload.notes},
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/manual-authorization", response_model=FrontdeskBooking)
def record_manual_authorization(
    payload: FrontdeskManualAuthorizationRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    columns, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="reservations.mark_guaranteed",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    if payload.authorization_amount <= 0:
        raise HTTPException(status_code=400, detail="Authorization amount must be greater than zero.")
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "authorization_status": "manual_authorized",
            "authorization_amount": payload.authorization_amount,
            "authorization_type": payload.authorization_type or "offline",
            "authorization_code": payload.authorization_code,
            "authorization_notes": payload.authorization_notes,
            "authorization_recorded_by": actor["email"],
            "authorization_recorded_at": datetime.utcnow(),
        },
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=(
            "[Front Desk] Manual/offline authorization recorded. "
            f"Amount {payload.authorization_amount:.2f}; code {payload.authorization_code or 'not provided'}. "
            f"{payload.authorization_notes or ''}"
        ).strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="manual_authorization_recorded",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"authorization_status": getattr(row, "authorization_status", None)},
        new_value={
            "authorization_status": "manual_authorized",
            "authorization_amount": payload.authorization_amount,
            "authorization_type": payload.authorization_type or "offline",
            "authorization_code": payload.authorization_code,
        },
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/upsell", response_model=FrontdeskBooking)
def record_upsell_decision(
    payload: FrontdeskUpsellRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_frontdesk_workflow_columns(db)
    columns, select_sql, property_code, row = _require_frontdesk_workflow_booking(
        db,
        booking_id=payload.booking_id,
        property_code=payload.property_code,
    )
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.room_move",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    accepted = bool(payload.accepted)
    declined = bool(payload.declined) or (payload.offered and not accepted)
    _update_booking_workflow_fields(
        db,
        booking_id=payload.booking_id,
        property_code=property_code,
        fields={
            "upsell_offered": bool(payload.offered),
            "upsell_accepted": accepted,
            "upsell_declined": declined and not accepted,
            "upsell_from_room_type": payload.from_room_type or getattr(row, "room_type", None),
            "upsell_to_room_type": payload.to_room_type,
            "upsell_amount_per_night": payload.amount_per_night,
            "upsell_total_amount": payload.total_amount,
            "upsell_recorded_by": actor["email"],
            "upsell_recorded_at": datetime.utcnow(),
        },
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=(
            f"[Front Desk] Upsell {'accepted' if accepted else 'declined'}. "
            f"{payload.from_room_type or getattr(row, 'room_type', None) or 'Current room'} to {payload.to_room_type or 'upgrade option'}; "
            f"amount/night {payload.amount_per_night or 0:.2f}. {payload.notes or ''}"
        ).strip(),
    )
    action = "upsell_accepted" if accepted else "upsell_declined"
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action=action,
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"upsell_accepted": getattr(row, "upsell_accepted", None), "room_type": getattr(row, "room_type", None)},
        new_value={
            "upsell_offered": payload.offered,
            "upsell_accepted": accepted,
            "upsell_declined": declined and not accepted,
            "upsell_from_room_type": payload.from_room_type,
            "upsell_to_room_type": payload.to_room_type,
            "upsell_amount_per_night": payload.amount_per_night,
            "pricing_unchanged": True,
        },
    )
    db.commit()
    refreshed = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, refreshed)


@router.post("/check-in", response_model=FrontdeskBooking)
def check_in_booking(
    payload: FrontdeskActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date or row.check_in_date,
        module="frontdesk",
        action="check_in",
    )
    booking_status = str(row.booking_status or "").lower()
    if booking_status in {"in_house", "checked_in"}:
        raise HTTPException(status_code=409, detail="Reservation is already checked in.")
    if booking_status in {"cancelled", "no_show", "no-show"}:
        raise HTTPException(status_code=409, detail="Cancelled or no-show bookings cannot be checked in.")
    if booking_status == "checked_out":
        raise HTTPException(status_code=409, detail="Checked-out bookings cannot be checked in again.")

    payment_status = str(row.payment_status or "pending").lower()
    guaranteed_statuses = {
        "paid",
        "deposit_paid",
        "guaranteed",
        "card_guaranteed",
        "pay_at_hotel",
        "billing_approved",
        "direct_bill",
        "city_ledger",
    }
    if payment_status not in guaranteed_statuses and not payload.manager_override:
        _audit_check_in_blocked(
            db,
            property_code=property_code,
            actor_email=actor["email"],
            booking_id=payload.booking_id,
            reason="Guarantee or deposit is required before check-in.",
            row=row,
        )
        raise HTTPException(
            status_code=409,
            detail="Guarantee or deposit is required before check-in. Use manager override only with approved billing or guarantee review.",
        )
    if payment_status not in guaranteed_statuses and payload.manager_override:
        require_pms_permission(
            db,
            permission_key="reservations.mark_guaranteed",
            property_code=property_code,
            user_email=x_pms_user_email,
        )
        if not payload.override_reason:
            raise HTTPException(status_code=400, detail="Manager override reason is required.")

    room_number = str(row.room_number or "").strip()
    if not room_number:
        _audit_check_in_blocked(
            db,
            property_code=property_code,
            actor_email=actor["email"],
            booking_id=payload.booking_id,
            reason="Room assignment required before check-in.",
            row=row,
        )
        raise HTTPException(
            status_code=409,
            detail="Room assignment required before check-in. Assign a clean or inspected room first.",
        )

    readiness = _room_readiness(db, property_code, room_number)
    if not readiness["ready_for_checkin"]:
        if readiness.get("clean_but_uninspected") and payload.manager_override:
            require_pms_permission(
                db,
                permission_key="housekeeping.mark_inspected",
                property_code=property_code,
                user_email=x_pms_user_email,
            )
            if not payload.override_reason:
                raise HTTPException(status_code=400, detail="Inspection override reason is required.")
        else:
            _audit_check_in_blocked(
                db,
                property_code=property_code,
                actor_email=actor["email"],
                booking_id=payload.booking_id,
                reason=f"Room {room_number} is not ready. Current status: {readiness['status']}.",
                row=row,
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Room {room_number} is not ready for check-in. "
                    f"Current status: {readiness['status']}. Housekeeping supervisor must mark it inspected before arrival."
                ),
            )

    deposit_accounts = db.execute(
        text(
            """
            SELECT id FROM deposit_accounts
            WHERE property_code = :property_code
              AND booking_id = :booking_id
              AND paid_amount > transferred_amount + refunded_amount + forfeited_amount
            FOR UPDATE
            """
        ),
        {"property_code": property_code, "booking_id": payload.booking_id},
    ).all() if _table_exists(db, "deposit_accounts") else []
    for deposit_account in deposit_accounts:
        transfer_deposit_to_folio(
            db,
            property_code=property_code,
            account_id=int(deposit_account.id),
            business_date=payload.business_date or row.check_in_date,
            amount=None,
            actor=actor["email"],
            idempotency_key=f"checkin-transfer:{property_code}:{payload.booking_id}:{deposit_account.id}",
        )

    update_sql = text(
        """
        UPDATE bookings
        SET booking_status = 'in_house'
        WHERE id = :id
          AND property_code = :property_code
        """
    )
    db.execute(update_sql, {"id": payload.booking_id, "property_code": property_code})
    _set_housekeeping_status(
        db,
        business_date=payload.business_date or row.check_in_date,
        property_code=property_code,
        room_number=room_number,
        hk_status="occupied_clean",
        user_email="frontdesk@guzo.local",
        action="room_marked_occupied_after_check_in",
        note=f"Booking {payload.booking_id} checked in.",
    )
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=row.guest_name,
        email=getattr(row, "guest_email", None),
        notes=getattr(row, "notes", None),
    )
    link_guest_profile_to_booking(db, booking_id=payload.booking_id, guest_profile=guest_profile)
    welcome_status = queue_guest_notification(
        db,
        property_code=property_code,
        booking_id=payload.booking_id,
        guest_profile=guest_profile,
        guest_email=getattr(row, "guest_email", None),
        action="check_in_welcome",
        message=f"Dear {row.guest_name}, welcome. Your check-in is complete and our Front Desk team is ready to assist you.",
        business_date=payload.business_date or row.check_in_date,
    )
    record_audit_log(
        db,
        action="guest_checked_in",
        entity_type="booking",
        entity_id=payload.booking_id,
        property_code=property_code,
        business_date=payload.business_date,
        details={"previous_status": row.booking_status},
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="guest_checked_in",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"booking_status": row.booking_status},
        new_value={
            "booking_status": "in_house",
            "room_number": room_number,
            "manager_override": payload.manager_override,
            "override_reason": payload.override_reason,
            "welcome_notification_status": welcome_status,
            "checked_in_from_q": getattr(row, "q_status", None) == "waiting",
        },
    )
    if getattr(row, "q_status", None) == "waiting":
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="frontdesk",
            action="check_in_completed_from_q",
            record_type="booking",
            record_id=payload.booking_id,
            old_value={"q_status": "waiting"},
            new_value={"booking_status": "in_house"},
        )
    db.commit()

    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/check-out", response_model=FrontdeskBooking)
def check_out_booking(
    payload: FrontdeskActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_out",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date or row.check_out_date,
        module="frontdesk",
        action="check_out",
    )
    booking_status = str(row.booking_status or "").lower()
    if booking_status not in {"in_house", "checked_in"}:
        raise HTTPException(status_code=409, detail="Only in-house guests can be checked out from Front Desk.")

    folio = _folio_row(db, property_code, payload.booking_id)
    balance = float(folio["balance"] or 0) if folio else 0.0
    payment_status = str(row.payment_status or "").lower()
    approved_billing = payment_status in {"direct_bill", "city_ledger", "billing_approved"}
    if abs(balance) >= 0.01 and not approved_billing:
        raise HTTPException(
            status_code=409,
            detail=f"Checkout blocked. Folio balance must be zero or transferred to approved billing. Balance: {balance:.2f}.",
        )

    update_sql = text(
        """
        UPDATE bookings
        SET booking_status = 'checked_out'
        WHERE id = :id
          AND property_code = :property_code
        """
    )
    db.execute(update_sql, {"id": payload.booking_id, "property_code": property_code})
    room_number = str(row.room_number or "").strip()
    if room_number:
        _set_housekeeping_status(
            db,
            business_date=payload.business_date or row.check_out_date,
            property_code=property_code,
            room_number=room_number,
            hk_status="vacant_dirty",
            user_email="frontdesk@guzo.local",
            action="room_marked_vacant_dirty_after_checkout",
            note=f"Booking {payload.booking_id} checked out.",
        )
    if folio:
        db.execute(
            text(
                """
                UPDATE folios
                SET status = CASE
                      WHEN ABS(COALESCE(balance, 0)) < 0.01 THEN 'closed'
                      ELSE 'transferred_to_billing'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :folio_id
                """
            ),
            {"folio_id": int(folio["id"])},
        )
    notification_status = _queue_guest_feedback_request(
        db,
        row=row,
        booking_id=payload.booking_id,
        property_code=property_code,
        business_date=payload.business_date or row.check_out_date,
    )
    record_audit_log(
        db,
        action="guest_checked_out",
        entity_type="booking",
        entity_id=payload.booking_id,
        property_code=property_code,
        business_date=payload.business_date,
        details={
            "previous_status": row.booking_status,
            "folio_id": int(folio["id"]) if folio else None,
            "balance": balance,
            "feedback_request_status": notification_status,
        },
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="guest_checked_out",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"booking_status": row.booking_status},
        new_value={
            "booking_status": "checked_out",
            "room_number": room_number or None,
            "room_status": "vacant_dirty" if room_number else None,
            "folio_id": int(folio["id"]) if folio else None,
            "folio_balance": balance,
            "feedback_request_status": notification_status,
        },
    )
    db.commit()

    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/room-move", response_model=FrontdeskBooking)
def move_guest_room(
    payload: FrontdeskStayActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.room_move",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    new_room = str(payload.room_number or "").strip()
    if not new_room:
        raise HTTPException(status_code=400, detail="New room number is required for room move.")
    if str(row.booking_status or "").lower() not in {"in_house", "checked_in"}:
        raise HTTPException(status_code=409, detail="Room move is available only for in-house guests.")
    readiness = _room_readiness(db, property_code, new_room)
    if not readiness["ready_for_checkin"]:
        raise HTTPException(
            status_code=409,
            detail=f"Room {new_room} is not ready for room move. Current status: {readiness['status']}.",
        )

    old_room = str(row.room_number or "").strip()
    db.execute(
        text(
            """
            UPDATE bookings
            SET room_number = :room_number
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {"room_number": new_room, "booking_id": payload.booking_id, "property_code": property_code},
    )
    business_date = payload.business_date or date.today()
    if old_room:
        _set_housekeeping_status(
            db,
            business_date=business_date,
            property_code=property_code,
            room_number=old_room,
            hk_status="vacant_dirty",
            user_email=actor["email"],
            action="room_move_old_room_dirty",
            note=f"Moved booking {payload.booking_id} from room {old_room} to {new_room}.",
        )
    _set_housekeeping_status(
        db,
        business_date=business_date,
        property_code=property_code,
        room_number=new_room,
        hk_status="occupied_clean",
        user_email=actor["email"],
        action="room_move_new_room_occupied",
        note=f"Moved booking {payload.booking_id} to room {new_room}.",
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Room move: {old_room or 'TBD'} to {new_room}. {payload.note or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="guest_room_moved",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"room_number": old_room},
        new_value={"room_number": new_room, "note": payload.note},
    )
    db.commit()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/extend-stay", response_model=FrontdeskBooking)
def extend_guest_stay(
    payload: FrontdeskStayActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.room_move",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    if not payload.check_out_date:
        raise HTTPException(status_code=400, detail="New check-out date is required.")
    if payload.check_out_date <= row.check_out_date:
        raise HTTPException(status_code=409, detail="Extended stay date must be after the current check-out date.")

    db.execute(
        text(
            """
            UPDATE bookings
            SET check_out_date = :check_out_date
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {"check_out_date": payload.check_out_date, "booking_id": payload.booking_id, "property_code": property_code},
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Stay extended to {payload.check_out_date.isoformat()}. {payload.note or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="guest_stay_extended",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"check_out_date": row.check_out_date.isoformat()},
        new_value={"check_out_date": payload.check_out_date.isoformat(), "note": payload.note},
    )
    db.commit()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/early-departure", response_model=FrontdeskBooking)
def mark_early_departure(
    payload: FrontdeskStayActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_out",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    departure_date = payload.business_date or date.today()
    if departure_date >= row.check_out_date:
        raise HTTPException(status_code=409, detail="Early departure date must be before scheduled check-out.")
    db.execute(
        text(
            """
            UPDATE bookings
            SET check_out_date = :check_out_date
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {"check_out_date": departure_date, "booking_id": payload.booking_id, "property_code": property_code},
    )
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Early departure set for {departure_date.isoformat()}. {payload.note or ''}".strip(),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="guest_early_departure",
        record_type="booking",
        record_id=payload.booking_id,
        old_value={"check_out_date": row.check_out_date.isoformat()},
        new_value={"check_out_date": departure_date.isoformat(), "note": payload.note},
    )
    db.commit()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)


@router.post("/late-checkout-note", response_model=FrontdeskBooking)
def add_late_checkout_note(
    payload: FrontdeskStayActionRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    columns = _booking_columns(db)
    select_sql = _select_frontdesk_booking_sql(columns)
    property_code = payload.property_code.strip().upper()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property")
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_out",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    note = payload.note or "Late checkout requested. Review policy, payment, and housekeeping impact."
    _append_booking_note(
        db,
        columns=columns,
        booking_id=payload.booking_id,
        property_code=property_code,
        note=f"[Front Desk] Late checkout note: {note}",
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="frontdesk",
        action="late_checkout_note_added",
        record_type="booking",
        record_id=payload.booking_id,
        new_value={"note": note},
    )
    db.commit()
    row = db.execute(select_sql, {"id": payload.booking_id, "property_code": property_code}).fetchone()
    return _frontdesk_booking_payload(db, row)
