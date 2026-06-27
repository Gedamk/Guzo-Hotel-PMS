from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.api.night_audit_api import _night_audit_exception_payload
from guzo_backend.dependencies import get_db
from guzo_backend.services.property_service import (
    ensure_property_table,
    get_property_by_code,
    get_property_by_id,
    list_properties,
    normalize_property_code,
    property_row_to_api,
)
from guzo_backend.services.rate_quote_service import ensure_rate_configuration_tables, get_rate_configuration
from guzo_backend.services.pms_security_service import (
    assign_pms_user_to_property,
    dev_auth_fallback_enabled,
    require_global_admin,
    require_pms_permission,
    require_property_access,
)

router = APIRouter(prefix="/admin", tags=["admin"])


DEFAULT_ROLE_ROWS = [
    {"role_key": "general_manager", "role_name": "General Manager", "description": "Full hotel operational oversight.", "is_system_role": True},
    {"role_key": "admin", "role_name": "System Administrator", "description": "System setup, security, integrations, and user control.", "is_system_role": True},
    {"role_key": "reservation_manager", "role_name": "Reservation Manager", "description": "Booking Hub approval, public request conversion, and reservations control.", "is_system_role": True},
    {"role_key": "front_desk_agent", "role_name": "Front Desk Agent", "description": "Arrivals, departures, room assignment, and Booking Hub request conversion.", "is_system_role": True},
    {"role_key": "frontdesk_agent", "role_name": "Front Desk Agent", "description": "Arrivals, departures, room assignment, and guest service.", "is_system_role": True},
    {"role_key": "reservations_agent", "role_name": "Reservations Agent", "description": "Direct, chatbot, Telegram, email, OTA, and group reservations.", "is_system_role": True},
    {"role_key": "housekeeping_supervisor", "role_name": "Housekeeping Supervisor", "description": "Room status, inspections, and housekeeping coordination.", "is_system_role": True},
    {"role_key": "finance_cashier", "role_name": "Finance Cashier", "description": "Folio payments, deposits, cashier controls, and finance reports.", "is_system_role": True},
    {"role_key": "night_auditor", "role_name": "Night Auditor", "description": "Night audit validation, close, and manager exception reporting.", "is_system_role": True},
    {"role_key": "fb_controller", "role_name": "F&B Controller", "description": "Food and beverage control and revenue posting review.", "is_system_role": True},
    {"role_key": "read_only_owner", "role_name": "Read Only Owner", "description": "Owner reporting view without operational posting rights.", "is_system_role": True},
]

DEFAULT_PERMISSION_MAP = {
    "general_manager": [
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "reservations.mark_guaranteed",
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.export_reports",
        "night_audit.run_validation",
        "night_audit.run_audit",
        "night_audit.override_exception",
        "night_audit.lock_date",
        "night_audit.roll_date",
        "reports.archive",
        "reports.email_manager",
        "reports.schedule",
        "admin.manage_users",
        "admin.manage_roles",
        "admin.view_audit_logs",
        "admin.manage_property_setup",
        "admin.manage_rate_configuration",
    ],
    "admin": [
        "admin.manage_users",
        "admin.manage_roles",
        "admin.view_audit_logs",
        "admin.manage_property_setup",
        "admin.manage_rate_configuration",
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "reservations.mark_guaranteed",
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.export_reports",
        "night_audit.run_validation",
        "night_audit.run_audit",
        "night_audit.override_exception",
        "night_audit.lock_date",
        "night_audit.roll_date",
        "reports.archive",
        "reports.email_manager",
        "reports.schedule",
    ],
    "reservation_manager": [
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.mark_guaranteed",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
    ],
    "front_desk_agent": [
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "booking.review_public_request",
        "booking.convert_public_request",
    ],
    "frontdesk_agent": [
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "booking.review_public_request",
        "booking.convert_public_request",
    ],
    "reservations_agent": [
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.mark_guaranteed",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
    ],
    "housekeeping_supervisor": [
        "housekeeping.mark_cleaned",
        "housekeeping.mark_inspected",
        "housekeeping.room_status_override",
    ],
    "finance_cashier": [
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.export_reports",
    ],
    "night_auditor": [
        "night_audit.run_validation",
        "night_audit.run_audit",
        "night_audit.lock_date",
        "night_audit.roll_date",
        "reports.archive",
    ],
    "fb_controller": [
        "view_fb_control",
        "post_fb_adjustment",
        "view_revenue_reports",
    ],
    "read_only_owner": [
        "finance.export_reports",
    ],
}

DEFAULT_USER_ROWS = [
    {"full_name": "System Administrator", "email": "admin@guzo.local", "role_key": "admin"},
    {"full_name": "General Manager", "email": "manager@guzo.local", "role_key": "general_manager"},
    {"full_name": "Reservation Manager", "email": "reservation.manager@guzo.local", "role_key": "reservation_manager"},
    {"full_name": "Front Desk Agent", "email": "front.desk@guzo.local", "role_key": "front_desk_agent"},
    {"full_name": "Front Desk Agent", "email": "frontdesk@guzo.local", "role_key": "frontdesk_agent"},
    {"full_name": "Reservations Agent", "email": "reservations@guzo.local", "role_key": "reservations_agent"},
    {"full_name": "Housekeeping Supervisor", "email": "housekeeping@guzo.local", "role_key": "housekeeping_supervisor"},
    {"full_name": "Finance Cashier", "email": "finance@guzo.local", "role_key": "finance_cashier"},
    {"full_name": "Night Auditor", "email": "nightaudit@guzo.local", "role_key": "night_auditor"},
]


class AdminUserCreate(BaseModel):
    full_name: str
    email: str
    role_key: str
    property_code: str | None = None
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    role_key: str | None = None
    property_code: str | None = None
    is_active: bool | None = None


class PropertyCreate(BaseModel):
    name: str
    code: str
    address: str
    city: str
    country: str
    timezone: str
    currency: str
    phone: str
    email: str
    isActive: bool = True
    onboardingStatus: str = "not_started"


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    timezone: str | None = None
    currency: str | None = None
    phone: str | None = None
    email: str | None = None
    isActive: bool | None = None
    onboardingStatus: str | None = None


class AssignAdminPayload(BaseModel):
    user_email: str | None = None


DEMO_ROOM_ROWS = [
    {"room_number": "101", "room_type": "Standard Room", "floor": 1},
    {"room_number": "102", "room_type": "Standard Room", "floor": 1},
    {"room_number": "201", "room_type": "Twin Room", "floor": 2},
    {"room_number": "202", "room_type": "Deluxe Room", "floor": 2},
    {"room_number": "301", "room_type": "Suite", "floor": 3},
]


class RatePlanConfigIn(BaseModel):
    code: str
    name: str
    multiplier: float = 1
    requires_manager_approval: bool = False
    cancellation_policy: str | None = None
    is_active: bool = True


class RoomTypeRateConfigIn(BaseModel):
    room_type: str
    base_rate_etb: float
    currency: str = "ETB"
    is_active: bool = True


class TaxServiceRuleConfigIn(BaseModel):
    rule_name: str
    tax_percent: float = 0.15
    service_charge_percent: float = 0.10
    is_active: bool = True


class SeasonRuleConfigIn(BaseModel):
    id: int | None = None
    rule_name: str
    start_month: int
    end_month: int
    surcharge_percent: float = 0.15
    weekend_surcharge_percent: float = 0.10
    is_active: bool = True


class DepositPolicyConfigIn(BaseModel):
    rate_code: str
    deposit_percent: float = 0.25
    guarantee_required: bool = True
    policy_text: str | None = None
    is_active: bool = True


class RateConfigurationUpdate(BaseModel):
    property_code: str
    rate_plans: list[RatePlanConfigIn] = []
    room_type_rates: list[RoomTypeRateConfigIn] = []
    tax_service_rules: list[TaxServiceRuleConfigIn] = []
    season_rules: list[SeasonRuleConfigIn] = []
    deposit_policies: list[DepositPolicyConfigIn] = []


def _normalize_property_code(property_code: str) -> str:
    return property_code.strip().upper()


def _clean_required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name} is required.")
    return cleaned


def _validate_onboarding_status(value: str) -> str:
    cleaned = value.strip() or "not_started"
    if cleaned not in {"not_started", "in_progress", "complete"}:
        raise HTTPException(status_code=400, detail="Invalid onboarding status.")
    return cleaned


def _go_live_check_payload(db: Session, property_row: dict[str, Any]) -> dict[str, Any]:
    property_code = property_row["property_code"]
    rooms_count = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": property_code},
    )
    active_rates = _count_table(
        db,
        "rate_plans",
        "WHERE property_code = :property_code AND COALESCE(is_active, TRUE) = TRUE",
        {"property_code": property_code},
    )
    tax_rules = _count_table(
        db,
        "tax_service_rules",
        "WHERE property_code = :property_code AND COALESCE(is_active, TRUE) = TRUE",
        {"property_code": property_code},
    )
    users_count = _count_table(
        db,
        "pms_users",
        "WHERE (property_code = :property_code OR property_code IS NULL) AND COALESCE(is_active, TRUE) = TRUE",
        {"property_code": property_code},
    )
    finance_users = _count_table(
        db,
        "pms_users",
        """
        WHERE (property_code = :property_code OR property_code IS NULL)
          AND role_key IN ('finance_cashier', 'finance_manager')
          AND COALESCE(is_active, TRUE) = TRUE
        """,
        {"property_code": property_code},
    )
    night_audit_ready = _table_exists(db, "business_date_locks") and _table_exists(db, "night_audit_postings")
    store_items = _count_table(
        db,
        "ingredients",
        "WHERE property_code = :property_code",
        {"property_code": property_code},
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if rooms_count == 0:
        blockers.append("No rooms are configured for this property.")
    if active_rates == 0:
        blockers.append("No active rate plans are configured.")
    if tax_rules == 0:
        blockers.append("No active tax/service rule is configured.")
    if users_count == 0:
        blockers.append("No active users are assigned to this property.")
    if finance_users == 0:
        blockers.append("No finance/cashier user setup is available.")
    if not night_audit_ready:
        blockers.append("Night audit/business date setup backend is not available.")
    if store_items == 0:
        warnings.append("F&B/store items are not configured yet.")

    status = "green"
    label = "Ready to Go Live"
    if blockers:
        status = "red"
        label = "Blocked from Operation"
    elif warnings:
        status = "yellow"
        label = "Setup Incomplete"

    return {
        "property_id": property_row["id"],
        "property_code": property_code,
        "status": status,
        "label": label,
        "ready": status == "green",
        "blockers": blockers,
        "warnings": warnings,
        "checks": {
            "rooms": rooms_count,
            "active_rates": active_rates,
            "tax_service_rules": tax_rules,
            "users": users_count,
            "finance_cashier_setup": finance_users,
            "night_audit_setup": night_audit_ready,
            "store_items": store_items,
        },
    }


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


def _ensure_hotel_row(db: Session, property_code: str, name: str) -> int | None:
    if not _table_exists(db, "hotels"):
        return None
    columns = _table_columns(db, "hotels")
    if not {"property_code", "name"}.issubset(columns):
        return None
    row = db.execute(
        text(
            """
            INSERT INTO hotels (property_code, name)
            VALUES (:property_code, :name)
            ON CONFLICT (property_code) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        ),
        {"property_code": property_code, "name": name},
    ).first()
    return int(row[0]) if row and row[0] is not None else None


def _upsert_demo_rooms(db: Session, property_row: dict[str, Any]) -> list[dict[str, Any]]:
    property_code = property_row["property_code"]
    if _table_exists(db, "rooms"):
        db.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS hotel_id INTEGER"))
    columns = _table_columns(db, "rooms")
    if not columns:
        raise HTTPException(status_code=409, detail="Room setup backend not connected yet.")

    hotel_id = _ensure_hotel_row(db, property_code, property_row["name"])
    seeded: list[dict[str, Any]] = []
    for room in DEMO_ROOM_ROWS:
        existing = db.execute(
            text(
                """
                SELECT id
                FROM rooms
                WHERE property_code = :property_code
                  AND room_number = :room_number
                LIMIT 1
                """
            ),
            {"property_code": property_code, "room_number": room["room_number"]},
        ).mappings().first()
        values = {
            "property_code": property_code,
            "room_number": room["room_number"],
            "room_type": room["room_type"],
            "floor": room["floor"],
            "hotel_id": hotel_id,
            "status": "available",
            "is_active": True,
        }
        if existing:
            assignments = [
                "room_type = :room_type" if "room_type" in columns else None,
                "floor = :floor" if "floor" in columns else None,
                "status = :status" if "status" in columns else None,
                "is_active = :is_active" if "is_active" in columns else None,
                "hotel_id = :hotel_id" if "hotel_id" in columns and hotel_id is not None else None,
            ]
            set_sql = ", ".join(item for item in assignments if item)
            if set_sql:
                db.execute(
                    text(
                        f"""
                        UPDATE rooms
                        SET {set_sql}
                        WHERE id = :room_id
                        """
                    ),
                    {**values, "room_id": existing["id"]},
                )
        else:
            insert_columns = ["property_code", "room_number"]
            if "room_type" in columns:
                insert_columns.append("room_type")
            if "floor" in columns:
                insert_columns.append("floor")
            if "status" in columns:
                insert_columns.append("status")
            if "is_active" in columns:
                insert_columns.append("is_active")
            if "hotel_id" in columns:
                if hotel_id is None:
                    raise HTTPException(status_code=409, detail="Rooms table requires hotel_id but hotel backend is not connected.")
                insert_columns.append("hotel_id")
            column_sql = ", ".join(insert_columns)
            value_sql = ", ".join(f":{column}" for column in insert_columns)
            db.execute(
                text(f"INSERT INTO rooms ({column_sql}) VALUES ({value_sql})"),
                values,
            )
        seeded.append({"property_code": property_code, **room})
    return seeded


def _delete_property_demo_room_inventory(db: Session, property_code: str) -> int:
    before = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": property_code},
    )
    if _table_exists(db, "housekeeping_status"):
        db.execute(
            text("DELETE FROM housekeeping_status WHERE property_code = :property_code"),
            {"property_code": property_code},
        )
    if _table_exists(db, "rooms"):
        db.execute(
            text("DELETE FROM rooms WHERE property_code = :property_code"),
            {"property_code": property_code},
        )
    return before


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


def _count_table(db: Session, table_name: str, where_sql: str = "", params: dict[str, Any] | None = None) -> int:
    if not _table_exists(db, table_name):
        return 0
    return int(
        db.execute(
            text(f"SELECT COUNT(*) FROM {table_name} {where_sql}"),
            params or {},
        ).scalar()
        or 0
    )


def _safe_rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params or {}).mappings().all()]


def _ensure_admin_identity_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pms_roles (
                id SERIAL PRIMARY KEY,
                role_key VARCHAR(80) UNIQUE NOT NULL,
                role_name VARCHAR(150) NOT NULL,
                description TEXT,
                is_system_role BOOLEAN DEFAULT FALSE
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pms_role_permissions (
                id SERIAL PRIMARY KEY,
                role_key VARCHAR(80) NOT NULL,
                permission_key VARCHAR(150) NOT NULL,
                allowed BOOLEAN DEFAULT TRUE,
                UNIQUE(role_key, permission_key)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pms_users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                role_key VARCHAR(80) NOT NULL,
                property_code VARCHAR(20),
                is_active BOOLEAN DEFAULT TRUE,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pms_user_property_assignments (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                assigned_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_email, property_code)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pms_audit_logs (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20),
                user_email VARCHAR(255),
                module VARCHAR(80),
                action VARCHAR(150),
                record_type VARCHAR(100),
                record_id VARCHAR(100),
                old_value JSONB,
                new_value JSONB,
                ip_address VARCHAR(80),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.commit()


def _seed_admin_identity_defaults(db: Session, property_code: str) -> None:
    _ensure_admin_identity_tables(db)
    for role in DEFAULT_ROLE_ROWS:
        db.execute(
            text(
                """
                INSERT INTO pms_roles (role_key, role_name, description, is_system_role)
                VALUES (:role_key, :role_name, :description, :is_system_role)
                ON CONFLICT (role_key) DO NOTHING
                """
            ),
            role,
        )

    for role_key, permissions in DEFAULT_PERMISSION_MAP.items():
        for permission_key in permissions:
            db.execute(
                text(
                    """
                    INSERT INTO pms_role_permissions (role_key, permission_key, allowed)
                    VALUES (:role_key, :permission_key, TRUE)
                    ON CONFLICT (role_key, permission_key) DO NOTHING
                    """
                ),
                {"role_key": role_key, "permission_key": permission_key},
            )

    for user in DEFAULT_USER_ROWS:
        db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES (:full_name, :email, :role_key, :property_code, TRUE)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {**user, "property_code": property_code},
        )
    db.execute(
        text(
            """
            UPDATE pms_users
            SET property_code = NULL
            WHERE LOWER(email) = LOWER('admin@guzo.local')
              AND role_key = 'admin'
            """
        )
    )
    db.commit()


def _record_pms_audit_log(
    db: Session,
    *,
    property_code: str | None,
    user_email: str,
    module: str,
    action: str,
    record_type: str,
    record_id: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    _ensure_admin_identity_tables(db)
    db.execute(
        text(
            """
            INSERT INTO pms_audit_logs (
              property_code, user_email, module, action, record_type, record_id, old_value, new_value
            )
            VALUES (
              :property_code, :user_email, :module, :action, :record_type, :record_id,
              CAST(:old_value AS JSONB), CAST(:new_value AS JSONB)
            )
            """
        ),
        {
            "property_code": property_code,
            "user_email": user_email,
            "module": module,
            "action": action,
            "record_type": record_type,
            "record_id": record_id,
            "old_value": json.dumps(old_value or {}, default=str),
            "new_value": json.dumps(new_value or {}, default=str),
        },
    )


def _role_permission_rows(db: Session) -> list[dict[str, Any]]:
    rows = _safe_rows(
        db,
        """
        SELECT
          r.role_key,
          r.role_name,
          p.permission_key
        FROM pms_roles r
        LEFT JOIN pms_role_permissions p ON p.role_key = r.role_key
          AND p.allowed = TRUE
        GROUP BY r.role_key, r.role_name, r.is_system_role, p.permission_key
        ORDER BY r.is_system_role DESC, r.role_name, p.permission_key
        """,
    )
    matrix: dict[str, dict[str, Any]] = {}
    for row in rows:
        role_key = row["role_key"]
        matrix.setdefault(
            role_key,
            {
                "role_key": role_key,
                "role_name": row["role_name"],
                "permissions": [],
            },
        )
        if row.get("permission_key"):
            matrix[role_key]["permissions"].append(row["permission_key"])
    return list(matrix.values())


@router.get("/properties")
def get_admin_properties(
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    require_global_admin(db, user_email=x_pms_user_email)
    properties = list_properties(db)
    db.commit()
    return {"properties": properties}


@router.post("/properties")
def create_admin_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = normalize_property_code(payload.code)
    if not property_code:
        raise HTTPException(status_code=400, detail="Property code is required.")
    ensure_property_table(db)
    actor = require_global_admin(db, user_email=x_pms_user_email)
    if get_property_by_code(db, property_code):
        raise HTTPException(status_code=409, detail=f"Property code {property_code} already exists.")

    values = {
        "name": _clean_required(payload.name, "Hotel name"),
        "property_code": property_code,
        "address": _clean_required(payload.address, "Address"),
        "city": _clean_required(payload.city, "City"),
        "country": _clean_required(payload.country, "Country"),
        "timezone": _clean_required(payload.timezone, "Timezone"),
        "currency": _clean_required(payload.currency, "Currency").upper(),
        "phone": _clean_required(payload.phone, "Phone"),
        "email": _clean_required(payload.email, "Email").lower(),
        "is_active": payload.isActive,
        "onboarding_status": _validate_onboarding_status(payload.onboardingStatus),
    }
    row = db.execute(
        text(
            """
            INSERT INTO hotel_properties (
                name, property_code, address, city, country, timezone, currency,
                phone, email, is_active, onboarding_status, updated_at
            )
            VALUES (
                :name, :property_code, :address, :city, :country, :timezone, :currency,
                :phone, :email, :is_active, :onboarding_status, now()
            )
            RETURNING *
            """
        ),
        values,
    ).mappings().first()
    api_row = property_row_to_api(row)
    _record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="admin",
        action="property_created",
        record_type="hotel_property",
        record_id=str(row["id"]),
        new_value=api_row,
    )
    assign_pms_user_to_property(
        db,
        user_email=actor["email"],
        property_code=property_code,
        assigned_by=actor["email"],
    )
    _record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="admin",
        action="property_admin_assigned",
        record_type="pms_user",
        record_id=actor["email"],
        new_value={"property_code": property_code, "assignment": "creator"},
    )
    db.commit()
    return {"status": "created", "property": api_row}


@router.put("/properties/{property_id}")
def update_admin_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    actor = require_global_admin(db, user_email=x_pms_user_email)

    next_values = {
        "property_id": property_id,
        "name": _clean_required(payload.name, "Hotel name") if payload.name is not None else current["name"],
        "address": _clean_required(payload.address, "Address") if payload.address is not None else current["address"],
        "city": _clean_required(payload.city, "City") if payload.city is not None else current["city"],
        "country": _clean_required(payload.country, "Country") if payload.country is not None else current["country"],
        "timezone": _clean_required(payload.timezone, "Timezone") if payload.timezone is not None else current["timezone"],
        "currency": (_clean_required(payload.currency, "Currency").upper() if payload.currency is not None else current["currency"]),
        "phone": _clean_required(payload.phone, "Phone") if payload.phone is not None else current["phone"],
        "email": (_clean_required(payload.email, "Email").lower() if payload.email is not None else current["email"]),
        "is_active": payload.isActive if payload.isActive is not None else current["is_active"],
        "onboarding_status": (
            _validate_onboarding_status(payload.onboardingStatus)
            if payload.onboardingStatus is not None
            else current["onboarding_status"]
        ),
    }
    status_changed = bool(current["is_active"]) != bool(next_values["is_active"])
    row = db.execute(
        text(
            """
            UPDATE hotel_properties
            SET name = :name,
                address = :address,
                city = :city,
                country = :country,
                timezone = :timezone,
                currency = :currency,
                phone = :phone,
                email = :email,
                is_active = :is_active,
                onboarding_status = :onboarding_status,
                updated_at = now()
            WHERE id = :property_id
            RETURNING *
            """
        ),
        next_values,
    ).mappings().first()
    api_row = property_row_to_api(row)
    _record_pms_audit_log(
        db,
        property_code=row["property_code"],
        user_email=actor["email"],
        module="admin",
        action="property_status_changed" if status_changed else "property_updated",
        record_type="hotel_property",
        record_id=str(property_id),
        old_value=property_row_to_api(current),
        new_value=api_row,
    )
    db.commit()
    return {"status": "updated", "property": api_row}


@router.post("/properties/{property_id}/status")
def update_admin_property_status(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    if payload.isActive is None:
        raise HTTPException(status_code=400, detail="isActive is required.")
    return update_admin_property(property_id, payload, db, x_pms_user_email)


@router.post("/properties/{property_id}/assign-admin")
def assign_admin_to_property(
    property_id: int,
    payload: AssignAdminPayload | None = None,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_property_setup",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    target_email = (payload.user_email if payload and payload.user_email else actor["email"]).strip().lower()
    user = db.execute(
        text(
            """
            SELECT id, email, role_key, is_active
            FROM pms_users
            WHERE LOWER(email) = LOWER(:email)
            LIMIT 1
            """
        ),
        {"email": target_email},
    ).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="PMS user not found.")
    if not user["is_active"]:
        raise HTTPException(status_code=409, detail="Cannot assign an inactive PMS user to a property.")

    assign_pms_user_to_property(
        db,
        user_email=target_email,
        property_code=current["property_code"],
        assigned_by=actor["email"],
    )
    _record_pms_audit_log(
        db,
        property_code=current["property_code"],
        user_email=actor["email"],
        module="admin",
        action="property_admin_assigned",
        record_type="pms_user",
        record_id=target_email,
        new_value={"property_code": current["property_code"]},
    )
    db.commit()
    return {
        "status": "assigned",
        "property_code": current["property_code"],
        "user_email": target_email,
    }


@router.get("/properties/{property_id}/go-live-check")
def get_property_go_live_check(
    property_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    require_pms_permission(
        db,
        permission_key="admin.manage_property_setup",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    payload = _go_live_check_payload(db, current)
    db.commit()
    return payload


@router.post("/properties/{property_id}/activate-live")
def activate_live_property(
    property_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_property_setup",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    check = _go_live_check_payload(db, current)
    if not check["ready"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Property is not ready to go live.",
                "status": check["status"],
                "blockers": check["blockers"],
                "warnings": check["warnings"],
            },
        )
    row = db.execute(
        text(
            """
            UPDATE hotel_properties
            SET is_active = TRUE,
                onboarding_status = 'complete',
                updated_at = now()
            WHERE id = :property_id
            RETURNING *
            """
        ),
        {"property_id": property_id},
    ).mappings().first()
    api_row = property_row_to_api(row)
    _record_pms_audit_log(
        db,
        property_code=row["property_code"],
        user_email=actor["email"],
        module="admin",
        action="property_activated_live",
        record_type="hotel_property",
        record_id=str(property_id),
        old_value=property_row_to_api(current),
        new_value={"property": api_row, "go_live_check": check},
    )
    db.commit()
    return {"status": "activated_live", "property": api_row, "go_live_check": check}


@router.post("/properties/{property_id}/seed-demo-rooms")
def seed_property_demo_rooms(
    property_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_property_setup",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    before = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": current["property_code"]},
    )
    seeded = _upsert_demo_rooms(db, current)
    after = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": current["property_code"]},
    )
    _record_pms_audit_log(
        db,
        property_code=current["property_code"],
        user_email=actor["email"],
        module="admin",
        action="property_demo_rooms_seeded",
        record_type="hotel_property",
        record_id=str(property_id),
        old_value={"room_count": before},
        new_value={"room_count": after, "rooms": seeded},
    )
    db.commit()
    return {
        "status": "seeded",
        "property_code": current["property_code"],
        "rooms": seeded,
        "room_count": after,
    }


@router.post("/properties/{property_id}/reset-demo-rooms")
def reset_property_demo_rooms(
    property_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    if not dev_auth_fallback_enabled():
        raise HTTPException(status_code=403, detail="Reset demo rooms is available only in local/demo mode.")
    ensure_property_table(db)
    current = get_property_by_id(db, property_id)
    if not current:
        raise HTTPException(status_code=404, detail="Property not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_property_setup",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    before = _delete_property_demo_room_inventory(db, current["property_code"])
    seeded = _upsert_demo_rooms(db, current)
    after = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": current["property_code"]},
    )
    _record_pms_audit_log(
        db,
        property_code=current["property_code"],
        user_email=actor["email"],
        module="admin",
        action="property_demo_rooms_reset",
        record_type="hotel_property",
        record_id=str(property_id),
        old_value={"room_count": before},
        new_value={"room_count": after, "rooms": seeded},
    )
    db.commit()
    return {
        "status": "reset",
        "property_code": current["property_code"],
        "rooms": seeded,
        "room_count": after,
    }


@router.get("/overview")
def get_admin_overview(
    property_code: str = Query(..., min_length=1),
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _seed_admin_identity_defaults(db, property_code)
    night_audit = _night_audit_exception_payload(db, property_code, business_date)

    archive_count = _count_table(
        db,
        "report_archive",
        "WHERE property_code = :property_code AND business_date = :business_date",
        {"property_code": property_code, "business_date": business_date},
    )
    scheduled_count = _count_table(
        db,
        "scheduled_reports",
        "WHERE property_code = :property_code AND COALESCE(is_active, TRUE) = TRUE",
        {"property_code": property_code},
    )
    notification_failures = _count_table(
        db,
        "guest_notification_outbox",
        "WHERE property_code = :property_code AND LOWER(COALESCE(status, 'pending')) IN ('failed', 'error')",
        {"property_code": property_code},
    )
    notification_pending = _count_table(
        db,
        "guest_notification_outbox",
        "WHERE property_code = :property_code AND LOWER(COALESCE(status, 'pending')) IN ('pending', 'pending_contact_review')",
        {"property_code": property_code},
    )
    notification_queued = _count_table(
        db,
        "guest_notification_outbox",
        "WHERE property_code = :property_code AND LOWER(COALESCE(status, 'queued')) = 'queued'",
        {"property_code": property_code},
    )
    notification_sent_today = _count_table(
        db,
        "guest_notification_outbox",
        "WHERE property_code = :property_code AND LOWER(COALESCE(status, '')) = 'sent' AND sent_at::date = :business_date",
        {"property_code": property_code, "business_date": business_date},
    )
    notification_last_sent = (
        db.execute(
            text(
                """
                SELECT MAX(sent_at)
                FROM guest_notification_outbox
                WHERE property_code = :property_code
                  AND sent_at IS NOT NULL
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if _table_exists(db, "guest_notification_outbox")
        else None
    )
    room_count = _count_table(
        db,
        "rooms",
        "WHERE property_code = :property_code",
        {"property_code": property_code},
    )
    active_user_count = _count_table(
        db,
        "pms_users",
        "WHERE (property_code = :property_code OR property_code IS NULL) AND COALESCE(is_active, TRUE) = TRUE",
        {"property_code": property_code},
    )

    archive_rows = (
        _safe_rows(
            db,
            """
            SELECT id, report_key, report_name, status, generated_by, generated_at
            FROM report_archive
            WHERE property_code = :property_code
            ORDER BY generated_at DESC, id DESC
            LIMIT 10
            """,
            {"property_code": property_code},
        )
        if _table_exists(db, "report_archive")
        else []
    )
    scheduled_rows = (
        _safe_rows(
            db,
            """
            SELECT id, report_key, report_name, recipient_email, frequency, schedule_time, is_active
            FROM scheduled_reports
            WHERE property_code = :property_code
            ORDER BY is_active DESC, schedule_time, id DESC
            LIMIT 10
            """,
            {"property_code": property_code},
        )
        if _table_exists(db, "scheduled_reports")
        else []
    )
    audit_rows = _safe_rows(
        db,
        """
        SELECT id, property_code, user_email, module, action, record_type, record_id, old_value, new_value, created_at
        FROM pms_audit_logs
        WHERE property_code = :property_code OR property_code IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 20
        """,
        {"property_code": property_code},
    )
    role_rows = _safe_rows(
        db,
        """
        SELECT role_key, role_name, description, is_system_role
        FROM pms_roles
        ORDER BY is_system_role DESC, role_name
        """,
    )
    permission_rows = _role_permission_rows(db)

    integrations = [
        {
            "key": "postgresql",
            "name": "PostgreSQL",
            "status": "online",
            "last_success": business_date.isoformat(),
            "secret_present": bool(os.getenv("POSTGRES_PASSWORD") or os.getenv("GUZO_DB_PASSWORD")),
        },
        {
            "key": "telegram",
            "name": "Telegram Bot",
            "status": "configured" if os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") else "not_configured",
            "last_success": None,
            "secret_present": bool(os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")),
        },
        {
            "key": "email",
            "name": "Email / SendGrid",
            "status": "configured" if os.getenv("SENDGRID_API_KEY") else "not_configured",
            "last_success": None,
            "secret_present": bool(os.getenv("SENDGRID_API_KEY")),
        },
        {
            "key": "reports",
            "name": "Report Archive",
            "status": "online" if _table_exists(db, "report_archive") else "not_started",
            "last_success": None,
            "secret_present": False,
        },
    ]

    admin_alerts: list[dict[str, Any]] = []
    if night_audit["blocking_count"]:
        admin_alerts.append(
            {
                "severity": "critical",
                "message": f"{night_audit['blocking_count']} Night Audit blocking exception(s) require manager attention.",
                "action": "Open Night Audit",
            }
        )
    if notification_failures:
        admin_alerts.append(
            {
                "severity": "warning",
                "message": f"{notification_failures} failed notification(s) require review.",
                "action": "Open Notification Outbox",
            }
        )
    if archive_count == 0:
        admin_alerts.append(
            {
                "severity": "warning",
                "message": "No report archive found for this business date.",
                "action": "Open Reports",
            }
        )

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "system_health": "online",
        "backend_status": "online",
        "database_status": "online",
        "frontend_status": "online",
        "business_date_status": "open",
        "night_audit_status": night_audit["audit_status"],
        "night_audit_blocking": night_audit["blocking_count"],
        "night_audit_warnings": night_audit["warning_count"],
        "active_users": active_user_count,
        "failed_logins": 0,
        "open_admin_alerts": len(admin_alerts),
        "room_count": room_count,
        "report_archive_count": archive_count,
        "scheduled_reports_count": scheduled_count,
        "notification_failures": notification_failures,
        "notification_pending": notification_pending,
        "roles": [row["role_key"] for row in role_rows],
        "role_details": role_rows,
        "permissions_matrix": permission_rows,
        "integrations": integrations,
        "admin_alerts": admin_alerts,
        "report_archive": archive_rows,
        "scheduled_reports": scheduled_rows,
        "audit_logs": audit_rows,
        "notification_outbox": {
            "pending": notification_pending,
            "queued": notification_queued,
            "sent_today": notification_sent_today,
            "failed": notification_failures,
            "last_sent_at": notification_last_sent.isoformat() if notification_last_sent else None,
        },
        "backup": {
            "last_backup_at": None,
            "status": "manual_export_ready",
        },
    }


@router.get("/users")
def get_admin_users(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _seed_admin_identity_defaults(db, property_code)
    return {
        "property_code": property_code,
        "users": _safe_rows(
            db,
            """
            SELECT id, full_name, email, role_key, property_code, is_active, last_login_at, created_at
            FROM pms_users
            WHERE property_code = :property_code
            ORDER BY is_active DESC, full_name
            """,
            {"property_code": property_code},
        ),
    }


@router.post("/users")
def create_admin_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    if not payload.property_code:
        raise HTTPException(status_code=400, detail="property_code is required.")
    property_code = _normalize_property_code(payload.property_code)
    _seed_admin_identity_defaults(db, property_code)
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_users",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    role_exists = db.execute(
        text("SELECT 1 FROM pms_roles WHERE role_key = :role_key"),
        {"role_key": payload.role_key},
    ).first()
    if not role_exists:
        raise HTTPException(status_code=400, detail="Unknown PMS role.")

    existing = db.execute(
        text("SELECT id FROM pms_users WHERE LOWER(email) = LOWER(:email)"),
        {"email": payload.email.strip()},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A PMS user with this email already exists.")

    row = db.execute(
        text(
            """
            INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
            VALUES (:full_name, :email, :role_key, :property_code, :is_active)
            RETURNING id, full_name, email, role_key, property_code, is_active, last_login_at, created_at
            """
        ),
        {
            "full_name": payload.full_name.strip(),
            "email": payload.email.strip().lower(),
            "role_key": payload.role_key,
            "property_code": property_code,
            "is_active": payload.is_active,
        },
    ).mappings().first()
    _record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="admin",
        action="pms_user_created",
        record_type="pms_user",
        record_id=str(row["id"]),
        new_value=dict(row),
    )
    db.commit()
    return {"status": "created", "user": dict(row)}


@router.patch("/users/{user_id}")
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_admin_identity_tables(db)
    current = db.execute(
        text("SELECT * FROM pms_users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="PMS user not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_users",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )

    updates = {
        "full_name": payload.full_name.strip() if payload.full_name is not None else current["full_name"],
        "role_key": payload.role_key if payload.role_key is not None else current["role_key"],
        "property_code": _normalize_property_code(payload.property_code) if payload.property_code is not None else current["property_code"],
        "is_active": payload.is_active if payload.is_active is not None else current["is_active"],
        "user_id": user_id,
    }
    role_exists = db.execute(
        text("SELECT 1 FROM pms_roles WHERE role_key = :role_key"),
        {"role_key": updates["role_key"]},
    ).first()
    if not role_exists:
        raise HTTPException(status_code=400, detail="Unknown PMS role.")

    row = db.execute(
        text(
            """
            UPDATE pms_users
            SET full_name = :full_name,
                role_key = :role_key,
                property_code = :property_code,
                is_active = :is_active
            WHERE id = :user_id
            RETURNING id, full_name, email, role_key, property_code, is_active, last_login_at, created_at
            """
        ),
        updates,
    ).mappings().first()
    _record_pms_audit_log(
        db,
        property_code=row["property_code"],
        user_email=actor["email"],
        module="admin",
        action="pms_user_updated",
        record_type="pms_user",
        record_id=str(user_id),
        old_value=dict(current),
        new_value=dict(row),
    )
    db.commit()
    return {"status": "updated", "user": dict(row)}


@router.post("/users/{user_id}/disable")
def disable_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_admin_identity_tables(db)
    current = db.execute(
        text("SELECT * FROM pms_users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="PMS user not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_users",
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    row = db.execute(
        text(
            """
            UPDATE pms_users
            SET is_active = FALSE
            WHERE id = :user_id
            RETURNING id, full_name, email, role_key, property_code, is_active, last_login_at, created_at
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    _record_pms_audit_log(
        db,
        property_code=row["property_code"],
        user_email=actor["email"],
        module="admin",
        action="pms_user_disabled",
        record_type="pms_user",
        record_id=str(user_id),
        old_value=dict(current),
        new_value=dict(row),
    )
    db.commit()
    return {"status": "disabled", "user": dict(row)}


@router.post("/users/{user_id}/reset-password")
def reset_admin_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    _ensure_admin_identity_tables(db)
    row = db.execute(
        text("SELECT id, full_name, email, role_key, property_code FROM pms_users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="PMS user not found.")
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_users",
        property_code=row["property_code"],
        user_email=x_pms_user_email,
    )
    _record_pms_audit_log(
        db,
        property_code=row["property_code"],
        user_email=actor["email"],
        module="admin",
        action="password_reset_requested",
        record_type="pms_user",
        record_id=str(user_id),
        new_value={"email": row["email"], "delivery": "admin_notice_placeholder"},
    )
    db.commit()
    return {
        "status": "queued",
        "message": "Password reset workflow recorded. Email/SMS delivery can be connected to the notification outbox.",
        "user": dict(row),
    }


@router.get("/roles")
def get_admin_roles(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _seed_admin_identity_defaults(db, property_code)
    return {
        "roles": _safe_rows(
            db,
            """
            SELECT role_key, role_name, description, is_system_role
            FROM pms_roles
            ORDER BY is_system_role DESC, role_name
            """,
        )
    }


@router.get("/permissions")
def get_admin_permissions(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _seed_admin_identity_defaults(db, property_code)
    return {"permissions": _role_permission_rows(db)}


@router.get("/rate-configuration")
def get_admin_rate_configuration(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    ensure_rate_configuration_tables(db, property_code)
    db.commit()
    return get_rate_configuration(db, property_code)


@router.put("/rate-configuration")
def update_admin_rate_configuration(
    payload: RateConfigurationUpdate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    _seed_admin_identity_defaults(db, property_code)
    ensure_rate_configuration_tables(db, property_code)
    actor = require_pms_permission(
        db,
        permission_key="admin.manage_rate_configuration",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    before = get_rate_configuration(db, property_code)

    for plan in payload.rate_plans:
        db.execute(
            text(
                """
                INSERT INTO rate_plans (
                    property_code, code, name, multiplier, requires_manager_approval,
                    cancellation_policy, is_active, updated_at
                )
                VALUES (
                    :property_code, :code, :name, :multiplier, :requires_manager_approval,
                    :cancellation_policy, :is_active, CURRENT_TIMESTAMP
                )
                ON CONFLICT (property_code, code) DO UPDATE
                SET name = EXCLUDED.name,
                    multiplier = EXCLUDED.multiplier,
                    requires_manager_approval = EXCLUDED.requires_manager_approval,
                    cancellation_policy = EXCLUDED.cancellation_policy,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {**plan.dict(), "property_code": property_code, "code": plan.code.strip().upper()},
        )

    for room_rate in payload.room_type_rates:
        db.execute(
            text(
                """
                INSERT INTO room_type_rates (
                    property_code, room_type, base_rate_etb, currency, is_active, updated_at
                )
                VALUES (
                    :property_code, :room_type, :base_rate_etb, :currency, :is_active, CURRENT_TIMESTAMP
                )
                ON CONFLICT (property_code, room_type) DO UPDATE
                SET base_rate_etb = EXCLUDED.base_rate_etb,
                    currency = EXCLUDED.currency,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {**room_rate.dict(), "property_code": property_code, "room_type": room_rate.room_type.strip()},
        )

    for rule in payload.tax_service_rules:
        db.execute(
            text(
                """
                INSERT INTO tax_service_rules (
                    property_code, rule_name, tax_percent, service_charge_percent, is_active, updated_at
                )
                VALUES (
                    :property_code, :rule_name, :tax_percent, :service_charge_percent, :is_active, CURRENT_TIMESTAMP
                )
                ON CONFLICT (property_code, rule_name) DO UPDATE
                SET tax_percent = EXCLUDED.tax_percent,
                    service_charge_percent = EXCLUDED.service_charge_percent,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {**rule.dict(), "property_code": property_code, "rule_name": rule.rule_name.strip()},
        )

    for rule in payload.season_rules:
        values = {**rule.dict(), "property_code": property_code, "rule_name": rule.rule_name.strip()}
        if rule.id:
            db.execute(
                text(
                    """
                    UPDATE season_rules
                    SET rule_name = :rule_name,
                        start_month = :start_month,
                        end_month = :end_month,
                        surcharge_percent = :surcharge_percent,
                        weekend_surcharge_percent = :weekend_surcharge_percent,
                        is_active = :is_active,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                      AND property_code = :property_code
                    """
                ),
                values,
            )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO season_rules (
                        property_code, rule_name, start_month, end_month,
                        surcharge_percent, weekend_surcharge_percent, is_active, updated_at
                    )
                    VALUES (
                        :property_code, :rule_name, :start_month, :end_month,
                        :surcharge_percent, :weekend_surcharge_percent, :is_active, CURRENT_TIMESTAMP
                    )
                    """
                ),
                values,
            )

    for policy in payload.deposit_policies:
        db.execute(
            text(
                """
                INSERT INTO deposit_policies (
                    property_code, rate_code, deposit_percent, guarantee_required,
                    policy_text, is_active, updated_at
                )
                VALUES (
                    :property_code, :rate_code, :deposit_percent, :guarantee_required,
                    :policy_text, :is_active, CURRENT_TIMESTAMP
                )
                ON CONFLICT (property_code, rate_code) DO UPDATE
                SET deposit_percent = EXCLUDED.deposit_percent,
                    guarantee_required = EXCLUDED.guarantee_required,
                    policy_text = EXCLUDED.policy_text,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {**policy.dict(), "property_code": property_code, "rate_code": policy.rate_code.strip().upper()},
        )

    after = get_rate_configuration(db, property_code)
    _record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="admin",
        action="rate_configuration_updated",
        record_type="rate_configuration",
        record_id=property_code,
        old_value=before,
        new_value=after,
    )
    db.commit()
    return after


@router.get("/audit-logs")
def get_pms_audit_logs(
    property_code: str = Query(..., min_length=1),
    module: str | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    _seed_admin_identity_defaults(db, property_code)
    require_pms_permission(
        db,
        permission_key="admin.view_audit_logs",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    module_filter = "AND module = :module" if module else ""
    params: dict[str, Any] = {"property_code": property_code}
    if module:
        params["module"] = module
    return {
        "property_code": property_code,
        "audit_logs": _safe_rows(
            db,
            f"""
            SELECT id, property_code, user_email, module, action, record_type, record_id, old_value, new_value, ip_address, created_at
            FROM pms_audit_logs
            WHERE property_code = :property_code
            {module_filter}
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            params,
        ),
    }
