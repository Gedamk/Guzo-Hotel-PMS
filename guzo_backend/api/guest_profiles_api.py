from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.guest_profile_service import ensure_guest_profile_tables
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission


router = APIRouter(prefix="/guest-profiles", tags=["guest-profiles"])


class GuestProfileUpdate(BaseModel):
    property_code: str = Field(..., min_length=1, max_length=20)
    guest_name: str | None = Field(None, max_length=150)
    phone: str | None = Field(None, max_length=80)
    email: str | None = Field(None, max_length=255)
    nationality: str | None = Field(None, max_length=100)
    id_passport_placeholder: str | None = Field(None, max_length=160)
    vip_flag: bool | None = None
    preferences: dict[str, Any] | None = None
    notes: str | None = None


def _row_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ["created_at", "updated_at"]:
        if item.get(key):
            item[key] = item[key].isoformat()
    return item


def _profile_by_guest_id(db: Session, property_code: str, guest_id: str) -> dict[str, Any]:
    ensure_guest_profile_tables(db)
    row = db.execute(
        text(
            """
            SELECT *
            FROM guest_profiles
            WHERE property_code = :property_code
              AND guest_id = :guest_id
            LIMIT 1
            """
        ),
        {"property_code": property_code.strip().upper(), "guest_id": guest_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Guest profile not found.")
    return _row_to_dict(row)


@router.get("")
def list_guest_profiles(
    property_code: str = Query(..., min_length=1),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="guest.view_profile",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    ensure_guest_profile_tables(db)
    clauses = ["property_code = :property_code"]
    params: dict[str, Any] = {"property_code": property_code}
    if search:
        clauses.append(
            """
            (
              LOWER(guest_name) LIKE :search
              OR LOWER(COALESCE(email, '')) LIKE :search
              OR COALESCE(phone, '') LIKE :search
              OR LOWER(guest_id) LIKE :search
            )
            """
        )
        params["search"] = f"%{search.strip().lower()}%"
    rows = db.execute(
        text(
            f"""
            SELECT *
            FROM guest_profiles
            WHERE {" AND ".join(clauses)}
            ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
            LIMIT 100
            """
        ),
        params,
    ).mappings().all()
    db.commit()
    return [_row_to_dict(row) for row in rows]


@router.get("/{guest_id}")
def get_guest_profile(
    guest_id: str,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    require_pms_permission(
        db,
        permission_key="guest.view_profile",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    profile = _profile_by_guest_id(db, property_code, guest_id)
    db.commit()
    return profile


@router.patch("/{guest_id}")
def update_guest_profile(
    guest_id: str,
    payload: GuestProfileUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = payload.property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="guest.edit_profile",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    before = _profile_by_guest_id(db, property_code, guest_id)
    updates = []
    params: dict[str, Any] = {"guest_id": guest_id, "property_code": property_code}
    for field in [
        "guest_name",
        "phone",
        "email",
        "nationality",
        "id_passport_placeholder",
        "vip_flag",
        "notes",
    ]:
        value = getattr(payload, field)
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    if payload.preferences is not None:
        updates.append("preferences = COALESCE(preferences, '{}'::jsonb) || CAST(:preferences AS JSONB)")
        import json

        params["preferences"] = json.dumps(payload.preferences, default=str)
    if not updates:
        return before
    updates.append("updated_at = now()")
    row = db.execute(
        text(
            f"""
            UPDATE guest_profiles
            SET {", ".join(updates)}
            WHERE guest_id = :guest_id
              AND property_code = :property_code
            RETURNING *
            """
        ),
        params,
    ).mappings().first()
    updated = _row_to_dict(row)
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="guest_profile",
        action="guest_profile_updated",
        record_type="guest_profile",
        record_id=guest_id,
        old_value=before,
        new_value=updated,
    )
    db.commit()
    return updated
