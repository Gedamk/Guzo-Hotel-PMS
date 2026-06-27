from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.guest_profile_service import ensure_guest_notification_outbox
from guzo_backend.services.notification_delivery_service import process_email_outbox, retry_notification
from guzo_backend.services.pms_security_service import require_pms_permission


router = APIRouter(prefix="/notifications", tags=["notifications"])


def _row_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ["business_date", "sent_at", "failed_at", "last_attempt_at", "created_at"]:
        if item.get(key):
            item[key] = item[key].isoformat()
    return item


@router.get("/outbox")
def list_notification_outbox(
    property_code: str = Query(..., min_length=1),
    status_filter: str | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="notifications.view_queue",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    ensure_guest_notification_outbox(db)
    clauses = ["n.property_code = :property_code"]
    params: dict[str, Any] = {"property_code": property_code}
    if status_filter:
        clauses.append("LOWER(n.status) = :status_filter")
        params["status_filter"] = status_filter.strip().lower()
    rows = db.execute(
        text(
            f"""
            SELECT n.id, n.property_code, n.booking_id, n.public_request_id, n.guest_profile_id, n.guest_id,
                   n.channel, n.recipient, n.action, n.message, n.business_date, n.status,
                   n.retry_count, n.attempt_count, n.sent_at, n.failed_at, n.failure_reason,
                   n.last_attempt_at, n.created_at
            FROM guest_notification_outbox n
            WHERE {" AND ".join(clauses)}
            ORDER BY n.created_at DESC, n.id DESC
            LIMIT 200
            """
        ),
        params,
    ).mappings().all()
    db.commit()
    return [_row_to_dict(row) for row in rows]


@router.post("/process-email-outbox")
def process_email_notification_outbox(
    property_code: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="notifications.retry_failed",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    result = process_email_outbox(db, property_code=property_code, actor_email=actor["email"], limit=limit)
    db.commit()
    return result


@router.post("/process-outbox")
def process_notification_outbox(
    property_code: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return process_email_notification_outbox(
        property_code=property_code,
        limit=limit,
        db=db,
        x_pms_user_email=x_pms_user_email,
    )


@router.post("/outbox/{notification_id}/retry")
def retry_failed_notification(
    notification_id: int,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="notifications.retry_failed",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    try:
        result = retry_notification(db, notification_id=notification_id, property_code=property_code, actor_email=actor["email"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.commit()
    return result
