from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.api.public_booking_requests_api import ensure_public_booking_requests_table
from guzo_backend.api.rooms_housekeeping_api import _set_housekeeping_status
from guzo_backend.services.auth_context import get_current_user_email
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission


SUPPORTED_TASKS = {
    "create_reservation_request",
    "suggest_room_assignment",
    "create_housekeeping_task",
    "explain_check_in_blocked",
    "summarize_front_desk_issues",
    "summarize_manager_alerts",
}


def _normalize_property_code(property_code: str | None) -> str:
    return (property_code or "DRE001").strip().upper()


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required field(s): {', '.join(missing)}")


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD")


def _room_status_expr(columns: set[str]) -> str:
    status_columns = [f"r.{column}" for column in ["hk_status", "housekeeping_status", "status"] if column in columns]
    if not status_columns:
        return "'vacant_clean'"
    return f"COALESCE({', '.join(status_columns)}, 'vacant_clean')"


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


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        ).first()
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="booking_id must be a valid integer")


def _guarantee_is_ready(payment_status: Any) -> bool:
    return str(payment_status or "").strip().lower() in {
        "paid",
        "deposit_paid",
        "guaranteed",
        "card_guaranteed",
        "pay_at_hotel",
        "billing_approved",
        "direct_bill",
        "city_ledger",
    }


def _room_readiness_for_agent(
    db: Session,
    *,
    property_code: str,
    room_number: str | None,
    business_date: date | None = None,
) -> dict[str, Any]:
    if not room_number:
        return {
            "room_number": None,
            "room_status": None,
            "is_occupied": None,
            "ready_for_check_in": False,
            "reason": "room_assignment_required",
        }

    columns = _table_columns(db, "rooms")
    status_expr = _room_status_expr(columns)
    occupied_expr = "COALESCE(r.is_occupied, false)" if "is_occupied" in columns else "false"
    room = db.execute(
        text(
            f"""
            SELECT r.room_number,
                   {status_expr} AS room_status,
                   {occupied_expr} AS is_occupied
            FROM rooms r
            WHERE r.property_code = :property_code
              AND CAST(r.room_number AS TEXT) = CAST(:room_number AS TEXT)
            LIMIT 1
            """
        ),
        {"property_code": property_code, "room_number": room_number},
    ).mappings().first()

    hk_status = None
    if _table_exists(db, "housekeeping_status"):
        hk_columns = _table_columns(db, "housekeeping_status")
        hk_order_parts = []
        if "updated_at" in hk_columns:
            hk_order_parts.append("updated_at DESC NULLS LAST")
        if "created_at" in hk_columns:
            hk_order_parts.append("created_at DESC NULLS LAST")
        if "id" in hk_columns:
            hk_order_parts.append("id DESC")
        hk_order = ", ".join(hk_order_parts) or "room_number"
        hk_status = db.execute(
            text(
                f"""
                SELECT hk_status
                FROM housekeeping_status
                WHERE property_code = :property_code
                  AND CAST(room_number AS TEXT) = CAST(:room_number AS TEXT)
                  AND (:business_date IS NULL OR business_date = :business_date)
                ORDER BY {hk_order}
                LIMIT 1
                """
            ),
            {"property_code": property_code, "room_number": room_number, "business_date": business_date},
        ).scalar()

    room_status = str((hk_status or (room["room_status"] if room else None) or "unknown")).strip().lower()
    is_occupied = bool(room["is_occupied"]) if room else False
    ready = not is_occupied and room_status in {"inspected", "vacant_inspected"}
    if ready:
        reason = "ready"
    elif is_occupied:
        reason = "room_occupied"
    elif room_status in {"vacant_clean", "clean"}:
        reason = "inspection_required"
    else:
        reason = "room_not_ready"
    return {
        "room_number": room_number,
        "room_status": room_status,
        "is_occupied": is_occupied,
        "ready_for_check_in": ready,
        "reason": reason,
    }


def create_reservation_request(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    actor = require_pms_permission(
        db,
        permission_key="booking.review_public_request",
        property_code=property_code,
        user_email=actor_email,
    )
    _require_fields(payload, ["guest_name", "check_in_date", "check_out_date", "room_type", "source"])
    check_in = _parse_date(payload["check_in_date"], "check_in_date")
    check_out = _parse_date(payload["check_out_date"], "check_out_date")
    if check_out <= check_in:
        raise HTTPException(status_code=400, detail="check_out_date must be after check_in_date")

    ensure_public_booking_requests_table(db)
    row = db.execute(
        text(
            """
            INSERT INTO public_booking_requests (
                property_code, source, channel, guest_name, guest_phone, guest_email,
                check_in_date, check_out_date, adults, children, room_type,
                reservation_type, booking_status, guarantee_type, deposit_status,
                special_requests, notes
            )
            VALUES (
                :property_code, :source, :channel, :guest_name, :guest_phone, :guest_email,
                :check_in_date, :check_out_date, :adults, :children, :room_type,
                'individual', 'pending_request', 'non_guaranteed', 'pending',
                :special_requests, :notes
            )
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "source": str(payload["source"]).strip(),
            "channel": payload.get("channel") or "agent_harness",
            "guest_name": str(payload["guest_name"]).strip(),
            "guest_phone": payload.get("guest_phone"),
            "guest_email": payload.get("guest_email"),
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": int(payload.get("adults") or 1),
            "children": int(payload.get("children") or 0),
            "room_type": str(payload["room_type"]).strip(),
            "special_requests": payload.get("special_requests"),
            "notes": payload.get("notes") or "Created by Agent Harness for manual Reservations review.",
        },
    ).first()
    request_id = int(row[0])
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_create_reservation_request",
        record_type="public_booking_request",
        record_id=request_id,
        new_value={"task_name": "create_reservation_request", "request_id": request_id},
    )
    return {
        "status": "created",
        "message": "Reservation request created for manual Booking Hub review.",
        "task_name": "create_reservation_request",
        "data": {"public_request_id": request_id, "booking_status": "pending_request"},
    }


def suggest_room_assignment(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["booking_id", "room_type", "check_in_date"])
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.open_folio",
        property_code=property_code,
        user_email=actor_email,
    )
    check_in = _parse_date(payload["check_in_date"], "check_in_date")
    room_type = str(payload["room_type"]).strip().lower()
    columns = _table_columns(db, "rooms")
    status_expr = _room_status_expr(columns)
    occupied_expr = "COALESCE(r.is_occupied, false)" if "is_occupied" in columns else "false"
    rows = db.execute(
        text(
            f"""
            SELECT r.room_number,
                   r.room_type,
                   {status_expr} AS room_status,
                   {occupied_expr} AS is_occupied
            FROM rooms r
            WHERE r.property_code = :property_code
              AND LOWER(COALESCE(r.room_type, '')) LIKE :room_type
              AND {occupied_expr} = FALSE
              AND LOWER({status_expr}) IN ('vacant_clean', 'vacant_inspected', 'inspected')
              AND NOT EXISTS (
                SELECT 1
                FROM bookings b
                WHERE b.property_code = r.property_code
                  AND CAST(b.room_number AS TEXT) = CAST(r.room_number AS TEXT)
                  AND LOWER(COALESCE(b.booking_status, '')) IN ('confirmed', 'in_house', 'checked_in')
                  AND b.check_in_date <= :check_in_date
                  AND b.check_out_date > :check_in_date
              )
            ORDER BY
              CASE WHEN LOWER({status_expr}) IN ('vacant_inspected', 'inspected') THEN 0 ELSE 1 END,
              r.room_number
            LIMIT 5
            """
        ),
        {
            "property_code": property_code,
            "room_type": f"%{room_type}%",
            "check_in_date": check_in,
        },
    ).mappings().all()
    suggestions = [dict(row) for row in rows]
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_suggest_room_assignment",
        record_type="booking",
        record_id=payload["booking_id"],
        new_value={"task_name": "suggest_room_assignment", "suggestion_count": len(suggestions)},
    )
    return {
        "status": "suggested",
        "message": "Room suggestions returned. No room was assigned.",
        "task_name": "suggest_room_assignment",
        "data": {"booking_id": payload["booking_id"], "suggested_rooms": suggestions},
    }


def create_housekeeping_task(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["room_number", "task_type", "priority"])
    actor = require_pms_permission(
        db,
        permission_key="housekeeping.mark_cleaned",
        property_code=property_code,
        user_email=actor_email,
    )
    task_type = str(payload["task_type"]).strip().lower()
    priority = str(payload["priority"]).strip().lower()
    business_date = _parse_date(payload.get("business_date") or date.today().isoformat(), "business_date")
    note = (
        f"Agent Harness housekeeping task: {task_type}; priority={priority}. "
        f"{payload.get('note') or ''}"
    ).strip()
    status_by_task = {
        "clean": "service_in_progress",
        "cleaning": "service_in_progress",
        "inspect": "vacant_clean",
        "inspection": "vacant_clean",
        "maintenance": "maintenance",
        "out_of_order": "out_of_order",
    }
    hk_status = status_by_task.get(task_type, "service_in_progress")
    _set_housekeeping_status(
        db,
        business_date=business_date,
        property_code=property_code,
        room_number=str(payload["room_number"]).strip(),
        hk_status=hk_status,
        user_email=actor["email"],
        action="agent_housekeeping_task_created",
        note=note,
        assigned_to=payload.get("assigned_to"),
        maintenance_note=payload.get("maintenance_note"),
        out_of_order_reason=payload.get("out_of_order_reason"),
        lost_item_note=payload.get("lost_item_note"),
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_create_housekeeping_task",
        record_type="housekeeping_status",
        record_id=str(payload["room_number"]),
        new_value={"task_name": "create_housekeeping_task", "task_type": task_type, "priority": priority},
    )
    return {
        "status": "created",
        "message": "Housekeeping task recorded on the room status board.",
        "task_name": "create_housekeeping_task",
        "data": {
            "room_number": str(payload["room_number"]).strip(),
            "task_type": task_type,
            "priority": priority,
            "hk_status": hk_status,
            "business_date": business_date.isoformat(),
        },
    }


def explain_check_in_blocked(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["booking_id"])
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=actor_email,
    )
    booking_id = _safe_int(payload["booking_id"])
    business_date = _parse_date(payload.get("business_date") or date.today().isoformat(), "business_date")
    booking = db.execute(
        text(
            """
            SELECT id, confirmation_id, guest_name, room_number, room_type,
                   check_in_date, check_out_date, booking_status, payment_status, notes
            FROM bookings
            WHERE id = :booking_id
              AND property_code = :property_code
            LIMIT 1
            """
        ),
        {"booking_id": booking_id, "property_code": property_code},
    ).mappings().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found for check-in explanation.")

    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    booking_status = str(booking["booking_status"] or "").strip().lower()
    if booking_status in {"in_house", "checked_in"}:
        blockers.append({"code": "already_checked_in", "message": "Reservation is already checked in."})
    if booking_status in {"cancelled", "canceled", "no_show", "checked_out"}:
        blockers.append({"code": "invalid_booking_status", "message": f"Booking status is {booking_status}."})
    if not booking["room_number"]:
        blockers.append({"code": "room_assignment_required", "message": "A room must be assigned before check-in."})
    if not _guarantee_is_ready(booking["payment_status"]):
        blockers.append(
            {
                "code": "guarantee_required",
                "message": "Deposit, guarantee, pay-at-hotel approval, or approved billing is required.",
            }
        )

    room_readiness = _room_readiness_for_agent(
        db,
        property_code=property_code,
        room_number=booking["room_number"],
        business_date=business_date,
    )
    if booking["room_number"] and not room_readiness["ready_for_check_in"]:
        blockers.append(
            {
                "code": str(room_readiness["reason"]),
                "message": f"Room {booking['room_number']} is not inspected and ready for check-in.",
            }
        )

    if booking["check_in_date"] and booking["check_in_date"] != business_date:
        warnings.append(
            {
                "code": "arrival_date_mismatch",
                "message": f"Arrival date is {booking['check_in_date']}, not {business_date}.",
            }
        )

    result_status = "blocked" if blockers else "clear"
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_explain_check_in_blocked",
        record_type="booking",
        record_id=booking_id,
        new_value={"task_name": "explain_check_in_blocked", "status": result_status, "blocker_count": len(blockers)},
    )
    return {
        "status": result_status,
        "message": "Check-in blockers found." if blockers else "No check-in blockers found.",
        "task_name": "explain_check_in_blocked",
        "data": {
            "booking_id": booking_id,
            "guest_name": booking["guest_name"],
            "confirmation_id": booking["confirmation_id"],
            "booking_status": booking_status,
            "payment_status": booking["payment_status"],
            "room_readiness": room_readiness,
            "blockers": blockers,
            "warnings": warnings,
        },
    }


def summarize_front_desk_issues(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.open_folio",
        property_code=property_code,
        user_email=actor_email,
    )
    business_date = _parse_date(payload.get("business_date") or date.today().isoformat(), "business_date")
    pending_statuses = ("confirmed", "reserved", "pending", "pending_request", "pending_guarantee")
    arrival_rows = db.execute(
        text(
            """
            SELECT id, guest_name, room_number, payment_status, booking_status
            FROM bookings
            WHERE property_code = :property_code
              AND check_in_date = :business_date
              AND LOWER(COALESCE(booking_status, '')) = ANY(:pending_statuses)
            ORDER BY id
            """
        ),
        {"property_code": property_code, "business_date": business_date, "pending_statuses": list(pending_statuses)},
    ).mappings().all()
    departure_rows = db.execute(
        text(
            """
            SELECT id, guest_name, room_number, payment_status, booking_status
            FROM bookings
            WHERE property_code = :property_code
              AND check_out_date = :business_date
              AND LOWER(COALESCE(booking_status, '')) IN ('in_house', 'checked_in')
            ORDER BY id
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().all()
    no_show_candidates = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE property_code = :property_code
              AND check_in_date < :business_date
              AND LOWER(COALESCE(booking_status, '')) = ANY(:pending_statuses)
            """
        ),
        {"property_code": property_code, "business_date": business_date, "pending_statuses": list(pending_statuses)},
    ).scalar() or 0

    missing_room = [row for row in arrival_rows if not row["room_number"]]
    missing_guarantee = [row for row in arrival_rows if not _guarantee_is_ready(row["payment_status"])]
    room_readiness_exceptions = []
    for row in arrival_rows:
        if row["room_number"]:
            readiness = _room_readiness_for_agent(
                db,
                property_code=property_code,
                room_number=row["room_number"],
                business_date=business_date,
            )
            if not readiness["ready_for_check_in"]:
                room_readiness_exceptions.append(
                    {
                        "booking_id": row["id"],
                        "guest_name": row["guest_name"],
                        "room_number": row["room_number"],
                        "reason": readiness["reason"],
                        "room_status": readiness["room_status"],
                    }
                )

    issues = []
    if missing_room:
        issues.append({"code": "missing_room_assignment", "count": len(missing_room)})
    if missing_guarantee:
        issues.append({"code": "missing_guarantee", "count": len(missing_guarantee)})
    if room_readiness_exceptions:
        issues.append({"code": "room_readiness_exception", "count": len(room_readiness_exceptions)})
    if departure_rows:
        issues.append({"code": "pending_departures", "count": len(departure_rows)})
    if no_show_candidates:
        issues.append({"code": "no_show_candidates", "count": int(no_show_candidates)})

    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_summarize_front_desk_issues",
        record_type="business_date",
        record_id=business_date.isoformat(),
        new_value={"task_name": "summarize_front_desk_issues", "issue_count": len(issues)},
    )
    return {
        "status": "summary",
        "message": "Front Desk issue summary generated.",
        "task_name": "summarize_front_desk_issues",
        "data": {
            "business_date": business_date.isoformat(),
            "pending_arrivals": len(arrival_rows),
            "pending_departures": len(departure_rows),
            "missing_room_assignments": len(missing_room),
            "missing_guarantees": len(missing_guarantee),
            "room_readiness_exceptions": room_readiness_exceptions,
            "no_show_candidates": int(no_show_candidates),
            "issues": issues,
        },
    }


def summarize_manager_alerts(
    db: Session,
    *,
    property_code: str,
    actor_email: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    actor = require_pms_permission(
        db,
        permission_key="admin.view_audit_logs",
        property_code=property_code,
        user_email=actor_email,
    )
    if not _table_exists(db, "manager_alerts"):
        return {
            "status": "todo",
            "message": "manager_alerts table is not available yet; schema migration is required.",
            "task_name": "summarize_manager_alerts",
            "data": {"open_alert_count": 0, "alerts": []},
        }

    status = str(payload.get("status") or "open").strip().lower()
    rows = db.execute(
        text(
            """
            SELECT id, alert_type, severity, message, status, booking_id, created_at
            FROM manager_alerts
            WHERE property_code = :property_code
              AND LOWER(COALESCE(status, 'open')) = :status
            ORDER BY
              CASE LOWER(COALESCE(severity, 'medium'))
                WHEN 'urgent' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
              END,
              created_at DESC NULLS LAST,
              id DESC
            LIMIT 25
            """
        ),
        {"property_code": property_code, "status": status},
    ).mappings().all()
    by_severity: dict[str, int] = {}
    for row in rows:
        severity = str(row["severity"] or "medium").lower()
        by_severity[severity] = by_severity.get(severity, 0) + 1

    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="agent_harness",
        action="agent_summarize_manager_alerts",
        record_type="manager_alerts",
        record_id=status,
        new_value={"task_name": "summarize_manager_alerts", "alert_count": len(rows)},
    )
    return {
        "status": "summary",
        "message": "Pending manager alerts summarized.",
        "task_name": "summarize_manager_alerts",
        "data": {
            "alert_status": status,
            "open_alert_count": len(rows),
            "by_severity": by_severity,
            "alerts": [dict(row) for row in rows],
        },
    }


def run_agent_task(
    db: Session,
    *,
    task_name: str,
    property_code: str | None,
    payload: dict[str, Any],
    actor_email: str | None,
) -> dict[str, Any]:
    actor_email = actor_email or get_current_user_email()
    if not actor_email:
        raise HTTPException(status_code=400, detail="X-PMS-User-Email header is required.")
    if task_name not in SUPPORTED_TASKS:
        raise HTTPException(status_code=400, detail=f"Unsupported Agent Harness task_name: {task_name}")
    normalized_property = _normalize_property_code(property_code or payload.get("property_code"))

    if task_name == "create_reservation_request":
        return create_reservation_request(
            db,
            property_code=normalized_property,
            actor_email=actor_email,
            payload=payload,
        )
    if task_name == "suggest_room_assignment":
        return suggest_room_assignment(
            db,
            property_code=normalized_property,
            actor_email=actor_email,
            payload=payload,
        )
    if task_name == "create_housekeeping_task":
        return create_housekeeping_task(
            db,
            property_code=normalized_property,
            actor_email=actor_email,
            payload=payload,
        )
    if task_name == "explain_check_in_blocked":
        return explain_check_in_blocked(
            db,
            property_code=normalized_property,
            actor_email=actor_email,
            payload=payload,
        )
    if task_name == "summarize_front_desk_issues":
        return summarize_front_desk_issues(
            db,
            property_code=normalized_property,
            actor_email=actor_email,
            payload=payload,
        )
    return summarize_manager_alerts(
        db,
        property_code=normalized_property,
        actor_email=actor_email,
        payload=payload,
    )
