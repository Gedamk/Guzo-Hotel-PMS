from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from guzo_backend.services.pms_security_service import (
    DEFAULT_USER_ROWS,
    ensure_pms_security_tables,
    normalize_property_code,
    record_pms_audit_log,
)


FRONTEND_ROLE_MAP = {
    "admin": "admin",
    "general_manager": "general_manager",
    "frontdesk_agent": "frontdesk",
    "reservations_agent": "reservation_agent",
    "housekeeping_supervisor": "housekeeping",
    "housekeeping_attendant": "housekeeping",
    "finance_cashier": "finance",
    "night_auditor": "night_auditor",
    "fb_controller": "fb_controller",
    "read_only_owner": "general_manager",
}

DEPARTMENT_MAP = {
    "admin": "it_admin",
    "general_manager": "executive",
    "frontdesk_agent": "frontdesk",
    "reservations_agent": "reservations",
    "housekeeping_supervisor": "housekeeping",
    "housekeeping_attendant": "housekeeping",
    "finance_cashier": "finance",
    "night_auditor": "night_audit",
    "fb_controller": "food_beverage",
    "read_only_owner": "executive",
}


def jwt_secret() -> str:
    return os.getenv("GUZO_JWT_SECRET") or os.getenv("SECRET_KEY") or "guzo-local-dev-change-me"


def jwt_algorithm() -> str:
    return "HS256"


def token_minutes() -> int:
    try:
        return max(int(os.getenv("GUZO_JWT_ACCESS_MINUTES", "720")), 5)
    except ValueError:
        return 720


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def ensure_auth_schema(db: Session, property_code: str | None = None) -> None:
    ensure_pms_security_tables(db, property_code)
    for sql in [
        "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS password_hash TEXT",
        "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMP",
        "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
        "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS property_code VARCHAR(20)",
        "UPDATE pms_users SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)",
    ]:
        db.execute(text(sql))

    default_password = os.getenv("GUZO_DEFAULT_ADMIN_PASSWORD", "admin123")
    default_hash = hash_password(default_password)
    for _full_name, email, _role_key in DEFAULT_USER_ROWS:
        db.execute(
            text(
                """
                UPDATE pms_users
                SET password_hash = COALESCE(password_hash, :password_hash),
                    updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(email) = LOWER(:email)
                """
            ),
            {"email": email, "password_hash": default_hash},
        )
    db.flush()


def pms_user_to_session(row: dict[str, Any]) -> dict[str, Any]:
    role_key = row["role_key"]
    property_code = normalize_property_code(row.get("property_code")) or "DRE001"
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["email"],
        "full_name": row["full_name"],
        "role_key": role_key,
        "role": FRONTEND_ROLE_MAP.get(role_key, "frontdesk"),
        "department": DEPARTMENT_MAP.get(role_key, "frontdesk"),
        "property_code": property_code,
        "property_codes": [property_code],
        "is_active": bool(row.get("is_active", True)),
    }


def get_user_by_email(db: Session, email: str, property_code: str | None = None) -> dict[str, Any] | None:
    ensure_auth_schema(db, property_code)
    normalized_property = normalize_property_code(property_code)
    row = db.execute(
        text(
            """
            SELECT id, full_name, email, role_key, property_code, is_active,
                   password_hash, created_at, updated_at, disabled_at, last_login_at
            FROM pms_users
            WHERE LOWER(email) = LOWER(:email)
              AND (:property_code IS NULL OR property_code = :property_code OR property_code IS NULL)
            ORDER BY property_code NULLS LAST, id
            LIMIT 1
            """
        ),
        {"email": email.strip().lower(), "property_code": normalized_property},
    ).mappings().first()
    return dict(row) if row else None


def create_access_token(user: dict[str, Any]) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=token_minutes())
    payload = {
        "sub": user["email"],
        "email": user["email"],
        "role_key": user["role_key"],
        "property_code": normalize_property_code(user.get("property_code")) or "DRE001",
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
        "iss": "guzo-pms",
    }
    return jwt.encode(payload, jwt_secret(), algorithm=jwt_algorithm()), expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()], issuer="guzo-pms")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Authentication token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    property_code: str | None = None,
) -> dict[str, Any]:
    user = get_user_by_email(db, email, property_code)
    normalized_property = normalize_property_code(property_code) or (user.get("property_code") if user else None)
    if not user or not verify_password(password, user.get("password_hash")):
        record_pms_audit_log(
            db,
            property_code=normalized_property,
            user_email=email,
            module="auth",
            action="login_failed",
            record_type="pms_user",
            record_id=email,
            new_value={"reason": "invalid_credentials"},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.get("is_active", True):
        record_pms_audit_log(
            db,
            property_code=normalized_property,
            user_email=email,
            module="auth",
            action="login_failed",
            record_type="pms_user",
            record_id=email,
            new_value={"reason": "disabled_user"},
        )
        db.commit()
        raise HTTPException(status_code=403, detail="PMS user is disabled.")
    db.execute(
        text("UPDATE pms_users SET last_login_at = CURRENT_TIMESTAMP WHERE id = :id"),
        {"id": user["id"]},
    )
    record_pms_audit_log(
        db,
        property_code=user.get("property_code"),
        user_email=user["email"],
        module="auth",
        action="login_success",
        record_type="pms_user",
        record_id=user["id"],
        new_value={"role_key": user["role_key"]},
    )
    db.flush()
    return user
