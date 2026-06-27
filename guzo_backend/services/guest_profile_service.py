from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


def _normalize_property_code(property_code: str | None) -> str:
    normalized = str(property_code or "").strip().upper()
    if not normalized or normalized in {"ALL", "*"}:
        raise ValueError("property_code is required for guest profile operations")
    return normalized


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str)


def ensure_guest_profile_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_profiles (
                id SERIAL PRIMARY KEY,
                guest_id VARCHAR(80) UNIQUE NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                guest_name VARCHAR(150) NOT NULL,
                phone VARCHAR(80),
                email VARCHAR(255),
                nationality VARCHAR(100),
                id_passport_placeholder VARCHAR(160),
                vip_flag BOOLEAN DEFAULT FALSE,
                preferences JSONB DEFAULT '{}'::jsonb,
                stay_history JSONB DEFAULT '[]'::jsonb,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ
            )
            """
        )
    )
    for statement in [
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS phone VARCHAR(80)",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS nationality VARCHAR(100)",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS id_passport_placeholder VARCHAR(160)",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS vip_flag BOOLEAN DEFAULT FALSE",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS stay_history JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    ]:
        db.execute(text(statement))

    for table_name in ["bookings", "public_booking_requests", "folios", "guest_feedback"]:
        if _table_exists(db, table_name):
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER"))
            db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)"))

    ensure_guest_notification_outbox(db)
    ensure_manager_alerts_table(db)


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


def ensure_guest_notification_outbox(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER,
                public_request_id INTEGER,
                guest_profile_id INTEGER,
                guest_id VARCHAR(80),
                property_code VARCHAR(50) NOT NULL,
                channel VARCHAR(50) NOT NULL,
                recipient TEXT,
                action VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                business_date DATE,
                status VARCHAR(50) NOT NULL DEFAULT 'queued',
                retry_count INTEGER DEFAULT 0,
                attempt_count INTEGER DEFAULT 0,
                sent_at TIMESTAMPTZ,
                failed_at TIMESTAMPTZ,
                failure_reason TEXT,
                last_attempt_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    for statement in [
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT",
        "ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ",
        "ALTER TABLE guest_notification_outbox ALTER COLUMN booking_id DROP NOT NULL",
        "UPDATE guest_notification_outbox SET retry_count = COALESCE(retry_count, attempt_count, 0)",
        "UPDATE guest_notification_outbox SET attempt_count = COALESCE(attempt_count, retry_count, 0)",
        "UPDATE guest_notification_outbox SET status = 'skipped' WHERE status = 'pending_contact_review'",
    ]:
        db.execute(text(statement))


def ensure_manager_alerts_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS manager_alerts (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                alert_type VARCHAR(100) NOT NULL,
                severity VARCHAR(30) DEFAULT 'warning',
                message TEXT NOT NULL,
                guest_profile_id INTEGER,
                guest_id VARCHAR(80),
                booking_id INTEGER,
                public_request_id INTEGER,
                business_date DATE,
                status VARCHAR(50) DEFAULT 'open',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                resolved_at TIMESTAMPTZ
            )
            """
        )
    )


def _guest_match_row(
    db: Session,
    *,
    property_code: str,
    guest_name: str,
    email: str | None,
    phone: str | None,
) -> Any:
    if email:
        row = db.execute(
            text(
                """
                SELECT *
                FROM guest_profiles
                WHERE property_code = :property_code
                  AND LOWER(COALESCE(email, '')) = LOWER(:email)
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_code": property_code, "email": email},
        ).mappings().first()
        if row:
            return row
    if phone:
        row = db.execute(
            text(
                """
                SELECT *
                FROM guest_profiles
                WHERE property_code = :property_code
                  AND COALESCE(phone, '') = :phone
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_code": property_code, "phone": phone},
        ).mappings().first()
        if row:
            return row
    return db.execute(
        text(
            """
            SELECT *
            FROM guest_profiles
            WHERE property_code = :property_code
              AND LOWER(guest_name) = LOWER(:guest_name)
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code, "guest_name": guest_name},
    ).mappings().first()


def find_or_create_guest_profile(
    db: Session,
    *,
    property_code: str,
    guest_name: str,
    email: str | None = None,
    phone: str | None = None,
    nationality: str | None = None,
    id_passport_placeholder: str | None = None,
    vip_flag: bool = False,
    preferences: dict[str, Any] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_guest_profile_tables(db)
    normalized_property = _normalize_property_code(property_code)
    normalized_name = (guest_name or "Guest").strip() or "Guest"
    existing = _guest_match_row(
        db,
        property_code=normalized_property,
        guest_name=normalized_name,
        email=email,
        phone=phone,
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE guest_profiles
                SET guest_name = COALESCE(NULLIF(:guest_name, ''), guest_name),
                    phone = COALESCE(NULLIF(:phone, ''), phone),
                    email = COALESCE(NULLIF(:email, ''), email),
                    nationality = COALESCE(NULLIF(:nationality, ''), nationality),
                    id_passport_placeholder = COALESCE(NULLIF(:id_passport_placeholder, ''), id_passport_placeholder),
                    vip_flag = COALESCE(vip_flag, FALSE) OR :vip_flag,
                    preferences = COALESCE(preferences, '{}'::jsonb) || CAST(:preferences AS JSONB),
                    notes = COALESCE(NULLIF(:notes, ''), notes),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": existing["id"],
                "guest_name": normalized_name,
                "phone": phone,
                "email": email,
                "nationality": nationality,
                "id_passport_placeholder": id_passport_placeholder,
                "vip_flag": bool(vip_flag),
                "preferences": _json(preferences),
                "notes": notes,
            },
        )
        row = db.execute(text("SELECT * FROM guest_profiles WHERE id = :id"), {"id": existing["id"]}).mappings().first()
        return dict(row)

    guest_id = f"GST-{normalized_property}-{uuid4().hex[:8].upper()}"
    row = db.execute(
        text(
            """
            INSERT INTO guest_profiles (
                guest_id, property_code, guest_name, phone, email, nationality,
                id_passport_placeholder, vip_flag, preferences, notes
            )
            VALUES (
                :guest_id, :property_code, :guest_name, :phone, :email, :nationality,
                :id_passport_placeholder, :vip_flag, CAST(:preferences AS JSONB), :notes
            )
            RETURNING *
            """
        ),
        {
            "guest_id": guest_id,
            "property_code": normalized_property,
            "guest_name": normalized_name,
            "phone": phone,
            "email": email,
            "nationality": nationality,
            "id_passport_placeholder": id_passport_placeholder,
            "vip_flag": bool(vip_flag),
            "preferences": _json(preferences),
            "notes": notes,
        },
    ).mappings().first()
    return dict(row)


def append_guest_stay_history(
    db: Session,
    *,
    guest_profile_id: int,
    event: dict[str, Any],
) -> None:
    db.execute(
        text(
            """
            UPDATE guest_profiles
            SET stay_history = COALESCE(stay_history, '[]'::jsonb) || CAST(:event AS JSONB),
                updated_at = now()
            WHERE id = :guest_profile_id
            """
        ),
        {"guest_profile_id": guest_profile_id, "event": _json([event])},
    )


def link_guest_profile_to_booking(db: Session, *, booking_id: int, guest_profile: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            UPDATE bookings
            SET guest_profile_id = :guest_profile_id,
                guest_id = :guest_id
            WHERE id = :booking_id
            """
        ),
        {"booking_id": booking_id, "guest_profile_id": guest_profile["id"], "guest_id": guest_profile["guest_id"]},
    )
    append_guest_stay_history(
        db,
        guest_profile_id=int(guest_profile["id"]),
        event={"booking_id": booking_id, "event": "reservation_linked", "date": date.today().isoformat()},
    )


def link_guest_profile_to_public_request(db: Session, *, request_id: int, guest_profile: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            UPDATE public_booking_requests
            SET guest_profile_id = :guest_profile_id,
                guest_id = :guest_id
            WHERE id = :request_id
            """
        ),
        {"request_id": request_id, "guest_profile_id": guest_profile["id"], "guest_id": guest_profile["guest_id"]},
    )


def link_guest_profile_to_folio(db: Session, *, folio_id: int, guest_profile: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            UPDATE folios
            SET guest_profile_id = :guest_profile_id,
                guest_id = :guest_id
            WHERE id = :folio_id
            """
        ),
        {"folio_id": folio_id, "guest_profile_id": guest_profile["id"], "guest_id": guest_profile["guest_id"]},
    )


def link_guest_profile_to_feedback(db: Session, *, feedback_id: int, guest_profile: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            UPDATE guest_feedback
            SET guest_profile_id = :guest_profile_id,
                guest_id = :guest_id
            WHERE id = :feedback_id
            """
        ),
        {"feedback_id": feedback_id, "guest_profile_id": guest_profile["id"], "guest_id": guest_profile["guest_id"]},
    )


def infer_notification_channel(*, email: str | None, phone: str | None, preferred_channel: str | None = None) -> tuple[str, str | None]:
    requested = (preferred_channel or "").strip().lower()
    if requested in {"telegram", "whatsapp", "sms"} and phone:
        return requested, phone
    if email:
        return "email", email
    if phone:
        return "sms", phone
    if requested in {"telegram", "whatsapp", "sms", "email"}:
        return requested, None
    return "staff_followup", None


def queue_guest_notification(
    db: Session,
    *,
    property_code: str,
    action: str,
    message: str,
    business_date: date | None = None,
    booking_id: int | None = None,
    public_request_id: int | None = None,
    guest_profile: dict[str, Any] | None = None,
    guest_email: str | None = None,
    guest_phone: str | None = None,
    channel: str | None = None,
) -> str:
    ensure_guest_notification_outbox(db)
    profile_email = guest_profile.get("email") if guest_profile else None
    profile_phone = guest_profile.get("phone") if guest_profile else None
    delivery_channel, recipient = infer_notification_channel(
        email=guest_email or profile_email,
        phone=guest_phone or profile_phone,
        preferred_channel=channel,
    )
    status = "queued" if recipient else "skipped"
    db.execute(
        text(
            """
            INSERT INTO guest_notification_outbox (
                booking_id, public_request_id, guest_profile_id, guest_id, property_code,
                channel, recipient, action, message, business_date, status, retry_count, attempt_count
            )
            VALUES (
                :booking_id, :public_request_id, :guest_profile_id, :guest_id, :property_code,
                :channel, :recipient, :action, :message, :business_date, :status, 0, 0
            )
            """
        ),
        {
            "booking_id": booking_id,
            "public_request_id": public_request_id,
            "guest_profile_id": guest_profile.get("id") if guest_profile else None,
            "guest_id": guest_profile.get("guest_id") if guest_profile else None,
            "property_code": _normalize_property_code(property_code),
            "channel": delivery_channel,
            "recipient": recipient,
            "action": action,
            "message": message,
            "business_date": business_date,
            "status": status,
        },
    )
    return status


def queue_manager_alert(
    db: Session,
    *,
    property_code: str,
    alert_type: str,
    message: str,
    severity: str = "warning",
    guest_profile: dict[str, Any] | None = None,
    booking_id: int | None = None,
    public_request_id: int | None = None,
    business_date: date | None = None,
) -> None:
    ensure_manager_alerts_table(db)
    db.execute(
        text(
            """
            INSERT INTO manager_alerts (
                property_code, alert_type, severity, message, guest_profile_id, guest_id,
                booking_id, public_request_id, business_date, status
            )
            VALUES (
                :property_code, :alert_type, :severity, :message, :guest_profile_id, :guest_id,
                :booking_id, :public_request_id, :business_date, 'open'
            )
            """
        ),
        {
            "property_code": _normalize_property_code(property_code),
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "guest_profile_id": guest_profile.get("id") if guest_profile else None,
            "guest_id": guest_profile.get("guest_id") if guest_profile else None,
            "booking_id": booking_id,
            "public_request_id": public_request_id,
            "business_date": business_date,
        },
    )


def queue_prearrival_deposit_alert_if_needed(
    db: Session,
    *,
    property_code: str,
    check_in_date: date,
    payment_status: str | None,
    guest_profile: dict[str, Any] | None,
    booking_id: int | None = None,
    public_request_id: int | None = None,
) -> None:
    if check_in_date > date.today() + timedelta(days=1):
        return
    if str(payment_status or "").lower() in {"paid", "deposit_paid", "guaranteed", "card_guaranteed", "direct_bill", "city_ledger"}:
        return
    queue_manager_alert(
        db,
        property_code=property_code,
        alert_type="missing_deposit_before_arrival",
        severity="high",
        message="Arrival is due soon and deposit or approved guarantee is still missing.",
        guest_profile=guest_profile,
        booking_id=booking_id,
        public_request_id=public_request_id,
        business_date=check_in_date,
    )
