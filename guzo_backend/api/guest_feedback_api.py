from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.guest_profile_service import (
    find_or_create_guest_profile,
    link_guest_profile_to_feedback,
    queue_manager_alert,
)
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_property_access


router = APIRouter(prefix="/guest-feedback", tags=["guest-feedback"])

FEEDBACK_STATUSES = {"new", "reviewed", "service_recovery", "closed"}


class GuestFeedbackCreate(BaseModel):
    property_code: str = Field(..., min_length=1, max_length=20)
    booking_id: int | None = None
    guest_name: str | None = Field(None, max_length=150)
    rating: float | None = Field(None, ge=0, le=5)
    feedback_source: str = Field("front_desk", max_length=50)
    comment: str | None = None
    status: str = "new"
    assigned_to: str | None = Field(None, max_length=150)
    priority: str = Field("medium", max_length=20)
    recovery_action: str | None = None
    follow_up_date: date | None = None
    resolution_notes: str | None = None
    guest_contacted: bool = False
    compensation_offered: str = Field("none", max_length=50)


class GuestFeedbackStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class GuestFeedbackServiceRecoveryUpdate(BaseModel):
    assigned_to: str | None = Field(None, max_length=150)
    priority: str = Field("medium", max_length=20)
    recovery_action: str | None = None
    follow_up_date: date | None = None
    resolution_notes: str | None = None
    guest_contacted: bool = False
    compensation_offered: str = Field("none", max_length=50)


def _normalize_property_code(property_code: str) -> str:
    return property_code.strip().upper()


def _ensure_guest_feedback_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_feedback (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                booking_id INTEGER,
                guest_name VARCHAR(150),
                rating NUMERIC(3, 2),
                feedback_source VARCHAR(50),
                comment TEXT,
                status VARCHAR(50) DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS booking_id INTEGER"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_name VARCHAR(150)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS feedback_source VARCHAR(50)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS comment TEXT"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'new'"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(150)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium'"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS recovery_action TEXT"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS follow_up_date DATE"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS resolution_notes TEXT"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_contacted BOOLEAN DEFAULT FALSE"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS compensation_offered VARCHAR(50) DEFAULT 'none'"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)"))


def _row_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    if item.get("rating") is not None:
        item["rating"] = float(item["rating"])
    if item.get("created_at"):
        item["created_at"] = item["created_at"].isoformat()
    if item.get("follow_up_date"):
        item["follow_up_date"] = item["follow_up_date"].isoformat()
    return item


def _feedback_row(db: Session, feedback_id: int, property_code: str) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, property_code, booking_id, guest_name, rating,
                   feedback_source, comment, status, created_at,
                   assigned_to, priority, recovery_action, follow_up_date,
                   resolution_notes, guest_contacted, compensation_offered
            FROM guest_feedback
            WHERE id = :feedback_id AND property_code = :property_code
            """
        ),
        {"feedback_id": feedback_id, "property_code": property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Guest feedback not found.")
    return _row_to_dict(row)


@router.get("")
def list_guest_feedback(
    property_code: str = Query(..., min_length=1),
    status_filter: str | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _ensure_guest_feedback_table(db)
    clauses = ["property_code = :property_code"]
    params: dict[str, Any] = {"property_code": property_code}
    if status_filter:
        clauses.append("LOWER(COALESCE(status, 'new')) = :status_filter")
        params["status_filter"] = status_filter.strip().lower()

    rows = db.execute(
        text(
            f"""
            SELECT id, property_code, booking_id, guest_name, rating,
                   feedback_source, comment, status, created_at,
                   assigned_to, priority, recovery_action, follow_up_date,
                   resolution_notes, guest_contacted, compensation_offered
            FROM guest_feedback
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """
        ),
        params,
    ).mappings().all()
    db.commit()
    return [_row_to_dict(row) for row in rows]


@router.post("")
def create_guest_feedback(
    payload: GuestFeedbackCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    status_value = payload.status.strip().lower()
    if status_value not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported feedback status: {payload.status}")

    _ensure_guest_feedback_table(db)
    booking_guest = None
    if payload.booking_id:
        booking_guest = db.execute(
            text(
                """
                SELECT guest_name, guest_email, guest_phone
                FROM bookings
                WHERE id = :booking_id
                  AND property_code = :property_code
                LIMIT 1
                """
            ),
            {"booking_id": payload.booking_id, "property_code": property_code},
        ).mappings().first()
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=payload.guest_name or (booking_guest or {}).get("guest_name") or "Guest",
        email=(booking_guest or {}).get("guest_email"),
        phone=(booking_guest or {}).get("guest_phone"),
        preferences={"feedback_source": payload.feedback_source},
    )
    row = db.execute(
        text(
            """
            INSERT INTO guest_feedback (
                property_code, booking_id, guest_name, rating,
                feedback_source, comment, status, assigned_to, priority,
                recovery_action, follow_up_date, resolution_notes,
                guest_contacted, compensation_offered
            )
            VALUES (
                :property_code, :booking_id, :guest_name, :rating,
                :feedback_source, :comment, :status, :assigned_to, :priority,
                :recovery_action, :follow_up_date, :resolution_notes,
                :guest_contacted, :compensation_offered
            )
            RETURNING id, property_code, booking_id, guest_name, rating,
                      feedback_source, comment, status, created_at,
                      assigned_to, priority, recovery_action, follow_up_date,
                      resolution_notes, guest_contacted, compensation_offered
            """
        ),
        {
            "property_code": property_code,
            "booking_id": payload.booking_id,
            "guest_name": payload.guest_name,
            "rating": payload.rating,
            "feedback_source": payload.feedback_source.strip().lower(),
            "comment": payload.comment,
            "status": status_value,
            "assigned_to": payload.assigned_to,
            "priority": payload.priority.strip().lower(),
            "recovery_action": payload.recovery_action,
            "follow_up_date": payload.follow_up_date,
            "resolution_notes": payload.resolution_notes,
            "guest_contacted": payload.guest_contacted,
            "compensation_offered": payload.compensation_offered.strip().lower(),
        },
    ).mappings().first()
    created = _row_to_dict(row)
    link_guest_profile_to_feedback(db, feedback_id=created["id"], guest_profile=guest_profile)
    created["guest_id"] = guest_profile["guest_id"]
    if payload.rating is not None and float(payload.rating) < 3:
        queue_manager_alert(
            db,
            property_code=property_code,
            alert_type="low_feedback_rating",
            severity="high",
            message=f"Low guest feedback rating {float(payload.rating):.1f}/5 requires manager review.",
            guest_profile=guest_profile,
            booking_id=payload.booking_id,
        )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=x_pms_user_email,
        module="guest_feedback",
        action="guest_feedback_created",
        record_type="guest_feedback",
        record_id=created["id"],
        new_value=created,
    )
    db.commit()
    return created


@router.patch("/{feedback_id}/status")
def update_guest_feedback_status(
    feedback_id: int,
    payload: GuestFeedbackStatusUpdate,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    status_value = payload.status.strip().lower()
    if status_value not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported feedback status: {payload.status}")

    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _ensure_guest_feedback_table(db)
    before = _feedback_row(db, feedback_id, property_code)
    row = db.execute(
        text(
            """
            UPDATE guest_feedback
            SET status = :status
            WHERE id = :feedback_id AND property_code = :property_code
            RETURNING id, property_code, booking_id, guest_name, rating,
                      feedback_source, comment, status, created_at,
                      assigned_to, priority, recovery_action, follow_up_date,
                      resolution_notes, guest_contacted, compensation_offered
            """
        ),
        {"feedback_id": feedback_id, "property_code": property_code, "status": status_value},
    ).mappings().first()
    updated = _row_to_dict(row)
    record_pms_audit_log(
        db,
        property_code=updated["property_code"],
        user_email=x_pms_user_email,
        module="guest_feedback",
        action=f"guest_feedback_{status_value}",
        record_type="guest_feedback",
        record_id=feedback_id,
        old_value=before,
        new_value={**updated, "note": payload.note},
    )
    db.commit()
    return updated


@router.patch("/{feedback_id}/service-recovery")
def mark_guest_feedback_service_recovery(
    feedback_id: int,
    payload: GuestFeedbackServiceRecoveryUpdate | None = None,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _ensure_guest_feedback_table(db)
    before = _feedback_row(db, feedback_id, property_code)
    details = payload or GuestFeedbackServiceRecoveryUpdate()
    row = db.execute(
        text(
            """
            UPDATE guest_feedback
            SET status = 'service_recovery',
                assigned_to = :assigned_to,
                priority = :priority,
                recovery_action = :recovery_action,
                follow_up_date = :follow_up_date,
                resolution_notes = :resolution_notes,
                guest_contacted = :guest_contacted,
                compensation_offered = :compensation_offered
            WHERE id = :feedback_id AND property_code = :property_code
            RETURNING id, property_code, booking_id, guest_name, rating,
                      feedback_source, comment, status, created_at,
                      assigned_to, priority, recovery_action, follow_up_date,
                      resolution_notes, guest_contacted, compensation_offered
            """
        ),
        {
            "feedback_id": feedback_id,
            "property_code": property_code,
            "assigned_to": details.assigned_to,
            "priority": details.priority.strip().lower(),
            "recovery_action": details.recovery_action,
            "follow_up_date": details.follow_up_date,
            "resolution_notes": details.resolution_notes,
            "guest_contacted": details.guest_contacted,
            "compensation_offered": details.compensation_offered.strip().lower(),
        },
    )
    updated = _row_to_dict(row.mappings().first())
    record_pms_audit_log(
        db,
        property_code=updated["property_code"],
        user_email=x_pms_user_email,
        module="guest_feedback",
        action="guest_feedback_service_recovery",
        record_type="guest_feedback",
        record_id=feedback_id,
        old_value=before,
        new_value=updated,
    )
    db.commit()
    return updated
