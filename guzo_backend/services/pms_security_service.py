from __future__ import annotations

import json
import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.auth_context import get_current_user_email


SYSTEM_ADMIN_EMAIL = "admin@guzo.local"
SYSTEM_AUDIT_EMAIL = "system@guzo.local"
GLOBAL_ADMIN_ROLES = {"super_admin"}

DEFAULT_ROLE_ROWS = [
    ("general_manager", "General Manager", "Full hotel operational oversight."),
    ("admin", "System Administrator", "System setup, security, integrations, and user control."),
    ("reservation_manager", "Reservation Manager", "Booking Hub approval, public request conversion, and reservations control."),
    ("front_desk_agent", "Front Desk Agent", "Arrivals, departures, room assignment, and Booking Hub request conversion."),
    # TODO: Remove legacy frontdesk_agent conversion support after all local/dev
    # accounts have migrated to front_desk_agent.
    ("frontdesk_agent", "Front Desk Agent", "Arrivals, departures, room assignment, and guest service."),
    ("reservations_agent", "Reservations Agent", "Direct, chatbot, Telegram, email, OTA, and group reservations."),
    ("housekeeping_supervisor", "Housekeeping Supervisor", "Room status, inspections, and housekeeping coordination."),
    ("housekeeping_attendant", "Housekeeping Attendant", "Room cleaning, dirty-room handling, and cleaned-room updates."),
    ("finance_cashier", "Finance Cashier", "Folio payments, deposits, cashier controls, and finance reports."),
    ("finance_manager", "Finance Manager", "F&B valuation, cost reports, finance review, and accounting controls."),
    ("night_auditor", "Night Auditor", "Night audit validation, close, and manager exception reporting."),
    ("fb_controller", "F&B Controller", "Food and beverage control and revenue posting review."),
    ("storekeeper", "Storekeeper", "Goods receiving, Main Store inventory, and approved stock issuing."),
    ("chef", "Chef", "Store requisitions and recipe draft preparation."),
    ("executive_chef", "Executive Chef", "Recipe approval, kitchen variance review, and chef controls."),
    ("fnb_manager", "F&B Manager", "Final F&B approval, purchasing review, and cost control reports."),
    ("purchasing_manager", "Purchasing Manager", "Supplier master, purchase orders, and purchase approvals."),
    ("read_only_owner", "Read Only Owner", "Owner reporting view without operational posting rights."),
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
        "reservations.modify_booking",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.transfer_balance",
        "finance.approve_variance",
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
        "guest.view_profile",
        "guest.edit_profile",
        "notifications.view_queue",
        "notifications.retry_failed",
        "agent.run_task",
        "housekeeping.mark_cleaned",
        "housekeeping.mark_inspected",
        "housekeeping.room_status_override",
        "fnb.create_purchase_order",
        "fnb.approve_purchase_order",
        "fnb.receive_goods",
        "fnb.request_stock",
        "fnb.issue_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.stock_count",
        "fnb.post_room_charge",
        "fnb.view_reports",
        "fnb.submit_report",
        "fnb.finance_review_report",
        "fnb.approve_report",
        "fnb.gm_lock_report",
        "fnb.override_report",
    ],
    "admin": [
        "admin.manage_users",
        "admin.manage_roles",
        "admin.view_audit_logs",
        "admin.manage_property_setup",
        "admin.manage_rate_configuration",
        "guest.view_profile",
        "guest.edit_profile",
        "notifications.view_queue",
        "notifications.retry_failed",
        "agent.run_task",
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
        "reservations.modify_booking",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.transfer_balance",
        "finance.approve_variance",
        "finance.export_reports",
        "night_audit.run_validation",
        "night_audit.run_audit",
        "night_audit.override_exception",
        "night_audit.lock_date",
        "night_audit.roll_date",
        "reports.archive",
        "reports.email_manager",
        "reports.schedule",
        "housekeeping.mark_cleaned",
        "housekeeping.mark_inspected",
        "housekeeping.room_status_override",
        "fnb.create_purchase_order",
        "fnb.approve_purchase_order",
        "fnb.receive_goods",
        "fnb.request_stock",
        "fnb.issue_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.stock_count",
        "fnb.post_room_charge",
        "fnb.view_reports",
        "fnb.submit_report",
        "fnb.finance_review_report",
        "fnb.approve_report",
        "fnb.gm_lock_report",
        "fnb.override_report",
    ],
    "reservation_manager": [
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.modify_booking",
        "reservations.mark_guaranteed",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "guest.view_profile",
        "agent.run_task",
    ],
    "front_desk_agent": [
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "booking.review_public_request",
        "booking.convert_public_request",
        "guest.view_profile",
        "agent.run_task",
    ],
    "frontdesk_agent": [
        "frontdesk.check_in",
        "frontdesk.check_out",
        "frontdesk.room_move",
        "frontdesk.open_folio",
        "booking.review_public_request",
        "booking.convert_public_request",
        "guest.view_profile",
        "agent.run_task",
    ],
    "reservations_agent": [
        "booking.review_public_request",
        "booking.reject_public_request",
        "booking.request_deposit",
        "booking.convert_public_request",
        "reservations.review_booking_request",
        "reservations.convert_booking",
        "reservations.modify_booking",
        "reservations.mark_guaranteed",
        "reservations.cancel_booking",
        "reservations.approve_pay_at_hotel",
        "reservations.send_deposit_link",
        "guest.view_profile",
        "agent.run_task",
    ],
    "finance_cashier": [
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.export_reports",
        "fnb.post_room_charge",
        "fnb.view_reports",
        "fnb.finance_review_report",
    ],
    "finance_manager": [
        "finance.post_payment",
        "finance.post_charge",
        "finance.record_deposit",
        "finance.close_cashier",
        "finance.void_transaction",
        "finance.transfer_balance",
        "finance.approve_variance",
        "finance.export_reports",
        "fnb.view_reports",
        "fnb.finance_review_report",
    ],
    "night_auditor": [
        "night_audit.run_validation",
        "night_audit.run_audit",
        "night_audit.lock_date",
        "night_audit.roll_date",
        "reports.archive",
    ],
    "housekeeping_supervisor": [
        "housekeeping.mark_cleaned",
        "housekeeping.mark_inspected",
        "housekeeping.room_status_override",
        "agent.run_task",
    ],
    "housekeeping_attendant": [
        "housekeeping.mark_cleaned",
    ],
    "read_only_owner": [
        "finance.export_reports",
        "fnb.view_reports",
    ],
    "fb_controller": [
        "fnb.create_purchase_order",
        "fnb.approve_purchase_order",
        "fnb.receive_goods",
        "fnb.request_stock",
        "fnb.issue_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.stock_count",
        "fnb.post_room_charge",
        "fnb.view_reports",
        "fnb.submit_report",
        "fnb.approve_report",
        "finance.post_charge",
        "finance.export_reports",
    ],
    "storekeeper": [
        "fnb.receive_goods",
        "fnb.issue_stock",
        "fnb.stock_count",
        "fnb.record_waste",
        "fnb.view_reports",
    ],
    "chef": [
        "fnb.request_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.view_reports",
        "fnb.submit_report",
    ],
    "executive_chef": [
        "fnb.request_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.view_reports",
        "fnb.submit_report",
        "fnb.approve_report",
    ],
    "fnb_manager": [
        "fnb.create_purchase_order",
        "fnb.approve_purchase_order",
        "fnb.receive_goods",
        "fnb.request_stock",
        "fnb.issue_stock",
        "fnb.manage_recipes",
        "fnb.record_waste",
        "fnb.stock_count",
        "fnb.post_room_charge",
        "fnb.view_reports",
        "fnb.submit_report",
        "fnb.approve_report",
    ],
    "purchasing_manager": [
        "fnb.create_purchase_order",
        "fnb.approve_purchase_order",
        "fnb.view_reports",
    ],
}

DEFAULT_USER_ROWS = [
    ("System Administrator", SYSTEM_ADMIN_EMAIL, "admin"),
    ("General Manager", "manager@guzo.local", "general_manager"),
    ("Reservation Manager", "reservation.manager@guzo.local", "reservation_manager"),
    ("Front Desk Agent", "front.desk@guzo.local", "front_desk_agent"),
    ("Front Desk Agent", "frontdesk@guzo.local", "frontdesk_agent"),
    ("Reservations Agent", "reservations@guzo.local", "reservations_agent"),
    ("Housekeeping Supervisor", "housekeeping@guzo.local", "housekeeping_supervisor"),
    ("Housekeeping Attendant", "attendant@guzo.local", "housekeeping_attendant"),
    ("Finance Cashier", "finance@guzo.local", "finance_cashier"),
    ("Finance Manager", "finance.manager@guzo.local", "finance_manager"),
    ("Night Auditor", "nightaudit@guzo.local", "night_auditor"),
    ("F&B Controller", "fnb@guzo.local", "fb_controller"),
    ("Storekeeper", "storekeeper@guzo.local", "storekeeper"),
    ("Chef", "chef@guzo.local", "chef"),
    ("Executive Chef", "executive.chef@guzo.local", "executive_chef"),
    ("F&B Manager", "fnb.manager@guzo.local", "fnb_manager"),
    ("Purchasing Manager", "purchasing@guzo.local", "purchasing_manager"),
]


def normalize_property_code(property_code: str | None) -> str | None:
    return property_code.strip().upper() if property_code else None


def dev_auth_fallback_enabled() -> bool:
    flag = os.getenv("GUZO_AUTH_DEV_FALLBACK")
    if flag is not None:
        return flag.strip().lower() in {"1", "true", "yes", "on"}
    app_env = os.getenv("APP_ENV", os.getenv("ENV", "")).strip().lower()
    return app_env in {"local", "dev", "development", "test"} or bool(os.getenv("TEST_DATABASE_URL"))


def _requested_user_email(user_email: str | None) -> str:
    context_email = get_current_user_email()
    if context_email:
        return context_email.strip().lower()
    if user_email and dev_auth_fallback_enabled():
        return user_email.strip().lower()
    if user_email:
        raise HTTPException(status_code=401, detail="Authentication token is required.")
    if dev_auth_fallback_enabled():
        return SYSTEM_ADMIN_EMAIL
    raise HTTPException(status_code=401, detail="Authentication token is required.")


def _property_exists(db: Session, property_code: str) -> bool:
    if db.execute(text("SELECT to_regclass('hotel_properties')")).scalar():
        property_row = db.execute(
            text("SELECT COALESCE(is_active, TRUE) FROM hotel_properties WHERE property_code = :property_code LIMIT 1"),
            {"property_code": property_code},
        ).first()
        if property_row is not None:
            return bool(property_row[0])
    if db.execute(text("SELECT to_regclass('hotels')")).scalar():
        if db.execute(
            text("SELECT 1 FROM hotels WHERE property_code = :property_code LIMIT 1"),
            {"property_code": property_code},
        ).first():
            return True
    return False


def require_property_access(
    db: Session,
    *,
    property_code: str | None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Validate a required property selection and the current user's access to it."""
    normalized_property = normalize_property_code(property_code)
    if not normalized_property or normalized_property in {"ALL", "*"}:
        raise HTTPException(status_code=400, detail="A specific property_code is required.")
    ensure_pms_security_tables(db, normalized_property)
    email = _requested_user_email(user_email)
    row = db.execute(
        text("""
            SELECT id, full_name, email, role_key, property_code, is_active
            FROM pms_users
            WHERE LOWER(email) = LOWER(:email)
            LIMIT 1
        """),
        {"email": email},
    ).mappings().first()
    if not row or not bool(row["is_active"]):
        _record_permission_denied(db, property_code=normalized_property, user_email=email, permission_key="property.access", reason="unknown_or_inactive_user", role_key=row["role_key"] if row else None)
        db.commit()
        raise HTTPException(status_code=403, detail="PMS user is inactive or unknown.")
    if not _property_exists(db, normalized_property):
        _record_permission_denied(db, property_code=normalized_property, user_email=email, permission_key="property.access", reason="unknown_property", role_key=row["role_key"])
        db.commit()
        raise HTTPException(status_code=404, detail=f"Property {normalized_property} was not found or is inactive.")
    is_global_admin = row["email"].lower() == SYSTEM_ADMIN_EMAIL or row["role_key"] in GLOBAL_ADMIN_ROLES
    if not is_global_admin and normalize_property_code(row["property_code"]) != normalized_property:
        assignment = db.execute(text("SELECT 1 FROM pms_user_property_assignments WHERE LOWER(user_email) = LOWER(:email) AND property_code = :property_code LIMIT 1"), {"email": email, "property_code": normalized_property}).first()
        if not assignment:
            _record_permission_denied(db, property_code=normalized_property, user_email=email, permission_key="property.access", reason="user_not_assigned_to_property", role_key=row["role_key"])
            db.commit()
            raise HTTPException(status_code=403, detail=f"Your user is not assigned to {_property_name_for_access_message(db, normalized_property)}.")
    return {**dict(row), "selected_property_code": normalized_property, "is_global_admin": is_global_admin}


def require_global_admin(db: Session, *, user_email: str | None = None) -> dict[str, Any]:
    ensure_pms_security_tables(db)
    email = _requested_user_email(user_email)
    row = db.execute(text("SELECT id, full_name, email, role_key, property_code, is_active FROM pms_users WHERE LOWER(email) = LOWER(:email) LIMIT 1"), {"email": email}).mappings().first()
    if not row or not bool(row["is_active"]):
        raise HTTPException(status_code=403, detail="PMS user is inactive or unknown.")
    if row["email"].lower() != SYSTEM_ADMIN_EMAIL and row["role_key"] not in GLOBAL_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Global administrator access is required.")
    return {**dict(row), "is_global_admin": True}


def accessible_property_codes(db: Session, *, user_email: str | None = None) -> set[str] | None:
    """Return assigned property codes, or None for a global administrator."""
    ensure_pms_security_tables(db)
    email = _requested_user_email(user_email)
    row = db.execute(
        text("SELECT email, role_key, property_code, is_active FROM pms_users WHERE LOWER(email) = LOWER(:email) LIMIT 1"),
        {"email": email},
    ).mappings().first()
    if not row or not bool(row["is_active"]):
        raise HTTPException(status_code=403, detail="PMS user is inactive or unknown.")
    if row["email"].lower() == SYSTEM_ADMIN_EMAIL or row["role_key"] in GLOBAL_ADMIN_ROLES:
        return None
    codes = {code for code in [normalize_property_code(row["property_code"])] if code}
    assignments = db.execute(
        text("SELECT property_code FROM pms_user_property_assignments WHERE LOWER(user_email) = LOWER(:email)"),
        {"email": email},
    ).scalars()
    codes.update(code for code in (normalize_property_code(value) for value in assignments) if code)
    return codes


def ensure_pms_security_tables(db: Session, property_code: str | None = None) -> None:
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

    normalized_property = normalize_property_code(property_code) or "DRE001"
    for role_key, role_name, description in DEFAULT_ROLE_ROWS:
        db.execute(
            text(
                """
                INSERT INTO pms_roles (role_key, role_name, description, is_system_role)
                VALUES (:role_key, :role_name, :description, TRUE)
                ON CONFLICT (role_key) DO NOTHING
                """
            ),
            {"role_key": role_key, "role_name": role_name, "description": description},
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

    for full_name, email, role_key in DEFAULT_USER_ROWS:
        db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES (:full_name, :email, :role_key, :property_code, TRUE)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {
                "full_name": full_name,
                "email": email,
                "role_key": role_key,
                "property_code": normalized_property,
            },
        )
    db.execute(
        text(
            """
            UPDATE pms_users
            SET property_code = NULL
            WHERE LOWER(email) = LOWER(:email)
              AND role_key = 'admin'
            """
        ),
        {"email": SYSTEM_ADMIN_EMAIL},
    )
    db.flush()


def assign_pms_user_to_property(
    db: Session,
    *,
    user_email: str,
    property_code: str,
    assigned_by: str | None = None,
) -> None:
    ensure_pms_security_tables(db, property_code)
    db.execute(
        text(
            """
            INSERT INTO pms_user_property_assignments (user_email, property_code, assigned_by)
            VALUES (LOWER(:user_email), :property_code, LOWER(:assigned_by))
            ON CONFLICT (user_email, property_code) DO NOTHING
            """
        ),
        {
            "user_email": user_email.strip().lower(),
            "property_code": normalize_property_code(property_code),
            "assigned_by": (assigned_by or SYSTEM_AUDIT_EMAIL).strip().lower(),
        },
    )


def _property_name_for_access_message(db: Session, property_code: str | None) -> str:
    if not property_code:
        return "this property"
    for table_name in ("hotel_properties", "hotels"):
        if not db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar():
            continue
        row = db.execute(
            text(f"SELECT name FROM {table_name} WHERE property_code = :property_code LIMIT 1"),
            {"property_code": property_code},
        ).first()
        if row and row[0]:
            return str(row[0])
    return property_code


def _record_permission_denied(
    db: Session,
    *,
    property_code: str | None,
    user_email: str | None,
    permission_key: str,
    reason: str,
    role_key: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO pms_audit_logs (
              property_code, user_email, module, action, record_type, record_id, old_value, new_value
            )
            VALUES (
              :property_code, :user_email, 'security', 'permission_denied',
              'pms_permission', :permission_key, CAST(:old_value AS JSONB), CAST(:new_value AS JSONB)
            )
            """
        ),
        {
            "property_code": normalize_property_code(property_code),
            "user_email": (user_email or SYSTEM_AUDIT_EMAIL).strip().lower(),
            "permission_key": permission_key,
            "old_value": json.dumps({"role_key": role_key}, default=str),
            "new_value": json.dumps(
                {"permission": permission_key, "reason": reason},
                default=str,
            ),
        },
    )


def require_pms_permission(
    db: Session,
    *,
    permission_key: str,
    property_code: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    ensure_pms_security_tables(db, property_code)
    normalized_property = normalize_property_code(property_code)
    if normalized_property:
        require_property_access(db, property_code=normalized_property, user_email=user_email)
    context_email = get_current_user_email()
    if context_email:
        email = context_email.strip().lower()
    elif user_email and dev_auth_fallback_enabled():
        email = user_email.strip().lower()
    elif user_email and not dev_auth_fallback_enabled():
        raise HTTPException(status_code=401, detail="Authentication token is required.")
    elif dev_auth_fallback_enabled():
        email = SYSTEM_ADMIN_EMAIL
    else:
        raise HTTPException(status_code=401, detail="Authentication token is required.")
    row = db.execute(
        text(
            """
            SELECT id, full_name, email, role_key, property_code, is_active
            FROM pms_users
            WHERE LOWER(email) = LOWER(:email)
              AND COALESCE(is_active, TRUE) = TRUE
            LIMIT 1
            """
        ),
        {"email": email},
    ).mappings().first()
    if not row:
        _record_permission_denied(
            db,
            property_code=property_code,
            user_email=email,
            permission_key=permission_key,
            reason="unknown_or_inactive_user",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="PMS user is inactive or unknown.")

    is_global_admin = row["email"].lower() == SYSTEM_ADMIN_EMAIL or row["role_key"] in GLOBAL_ADMIN_ROLES
    if normalized_property and not is_global_admin and row["property_code"] != normalized_property:
        assignment = db.execute(
            text(
                """
                SELECT 1
                FROM pms_user_property_assignments
                WHERE LOWER(user_email) = LOWER(:email)
                  AND property_code = :property_code
                LIMIT 1
                """
            ),
            {"email": email, "property_code": normalized_property},
        ).first()
        if not assignment:
            property_name = _property_name_for_access_message(db, normalized_property)
            _record_permission_denied(
                db,
                property_code=property_code,
                user_email=email,
                permission_key=permission_key,
                reason="user_not_assigned_to_property",
                role_key=row["role_key"],
            )
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=f"Your user is not assigned to {property_name}. Assign user access before operating this property.",
            )

    allowed = db.execute(
        text(
            """
            SELECT 1
            FROM pms_role_permissions
            WHERE role_key = :role_key
              AND permission_key = :permission_key
              AND COALESCE(allowed, TRUE) = TRUE
            LIMIT 1
            """
        ),
        {"role_key": row["role_key"], "permission_key": permission_key},
    ).first()
    if not allowed:
        _record_permission_denied(
            db,
            property_code=property_code,
            user_email=email,
            permission_key=permission_key,
            reason="role_permission_missing",
            role_key=row["role_key"],
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {permission_key}",
        )
    return dict(row)


def record_pms_audit_log(
    db: Session,
    *,
    property_code: str | None,
    user_email: str | None,
    module: str,
    action: str,
    record_type: str,
    record_id: str | int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    ensure_pms_security_tables(db, property_code)
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
            "property_code": normalize_property_code(property_code),
            "user_email": (user_email or SYSTEM_AUDIT_EMAIL).strip().lower(),
            "module": module,
            "action": action,
            "record_type": record_type,
            "record_id": str(record_id) if record_id is not None else None,
            "old_value": json.dumps(old_value or {}, default=str),
            "new_value": json.dumps(new_value or {}, default=str),
        },
    )
