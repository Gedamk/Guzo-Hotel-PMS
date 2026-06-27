from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.audit_log_service import record_audit_log
from guzo_backend.services.finance_transaction_service import post_finance_transaction
from guzo_backend.services.payment_lifecycle_service import allocate_deposit, receive_deposit, request_deposit
from guzo_backend.services.guest_profile_service import (
    find_or_create_guest_profile,
    link_guest_profile_to_booking,
    link_guest_profile_to_folio,
    link_guest_profile_to_public_request,
    queue_manager_alert,
    queue_prearrival_deposit_alert_if_needed,
)
from guzo_backend.services.pms_security_service import (
    record_pms_audit_log,
    require_pms_permission,
    require_property_access,
)
from guzo_backend.services.rate_quote_service import quote_stay

router = APIRouter(tags=["public-booking-requests"])


class PublicBookingRequestCreate(BaseModel):
    property_code: str = Field(..., min_length=1, max_length=20)
    source: str = "chatbot"
    channel: Optional[str] = None
    guest_name: str = Field(..., min_length=2, max_length=150)
    guest_phone: Optional[str] = Field(None, max_length=50)
    guest_email: Optional[str] = Field(None, max_length=150)
    check_in_date: date
    check_out_date: date
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    room_type: Optional[str] = Field(None, max_length=100)
    reservation_type: str = "individual"
    booking_status: str = "pending_request"
    guarantee_type: str = "non_guaranteed"
    deposit_status: str = "pending"
    special_requests: Optional[str] = None
    notes: Optional[str] = None

    @validator("check_out_date")
    def validate_dates(cls, value: date, values):
        check_in = values.get("check_in_date")
        if check_in and value <= check_in:
            raise ValueError("check_out_date must be after check_in_date")
        return value


class PublicBookingRequestOut(BaseModel):
    id: int
    property_code: str
    source: str
    channel: Optional[str] = None
    guest_name: str
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    check_in_date: date
    check_out_date: date
    adults: int
    children: int
    room_type: Optional[str] = None
    reservation_type: str
    booking_status: str
    guarantee_type: str
    deposit_status: str
    special_requests: Optional[str] = None
    notes: Optional[str] = None
    converted_booking_id: Optional[int] = None
    converted_at: Optional[datetime] = None
    converted_by: Optional[str] = None
    confirmation_id: Optional[str] = None
    guest_notification_status: Optional[str] = None
    deposit_payment_link: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PublicBookingRequestStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class PublicBookingRequestConvert(BaseModel):
    total_amount_etb: float = Field(0, ge=0)
    rate_per_night_etb: Optional[float] = Field(None, ge=0)
    room_type: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: str = "pending"
    notes: Optional[str] = None


class DepositPaymentWebhook(BaseModel):
    token: str = Field(..., min_length=16)
    status: str = Field(..., min_length=1)
    amount_etb: Optional[float] = Field(None, ge=0)
    provider: str = Field("manual_provider", max_length=80)
    provider_reference: Optional[str] = Field(None, max_length=160)
    failure_reason: Optional[str] = Field(None, max_length=500)
    paid_at: Optional[datetime] = None


REQUEST_STATUSES = {
    "pending_request",
    "reviewed",
    "rejected",
    "deposit_required",
    "deposit_requested",
    "tentative",
    "confirmed",
    "converted",
}

PUBLIC_REQUEST_CONVERT_PERMISSION = "booking.convert_public_request"
PUBLIC_REQUEST_CONVERT_ROLE_KEYS = {
    "admin",
    "reservation_manager",
    "front_desk_agent",
    "frontdesk_agent",
}
PUBLIC_REQUEST_CONVERT_DENIED_MESSAGE = (
    "Permission denied: converting public booking requests requires "
    "reservation_manager, front_desk_agent, or admin permission."
)


def ensure_public_booking_requests_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS public_booking_requests (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                source VARCHAR(50) DEFAULT 'chatbot',
                channel VARCHAR(50),
                guest_name VARCHAR(150) NOT NULL,
                guest_phone VARCHAR(50),
                guest_email VARCHAR(150),
                check_in_date DATE NOT NULL,
                check_out_date DATE NOT NULL,
                adults INTEGER DEFAULT 1,
                children INTEGER DEFAULT 0,
                room_type VARCHAR(100),
                reservation_type VARCHAR(50) DEFAULT 'individual',
                booking_status VARCHAR(50) DEFAULT 'pending_request',
                guarantee_type VARCHAR(50) DEFAULT 'non_guaranteed',
                deposit_status VARCHAR(50) DEFAULT 'pending',
                special_requests TEXT,
                notes TEXT,
                converted_booking_id INTEGER,
                converted_at TIMESTAMP,
                converted_by VARCHAR(150),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
    )
    db.execute(text("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_booking_id INTEGER"))
    db.execute(text("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_at TIMESTAMP"))
    db.execute(text("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_by VARCHAR(150)"))
    db.execute(text("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER"))
    db.execute(text("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)"))
    db.execute(
        text(
            """
            UPDATE public_booking_requests
            SET booking_status = 'converted',
                converted_at = COALESCE(converted_at, updated_at, CURRENT_TIMESTAMP),
                converted_by = COALESCE(converted_by, 'booking_hub_staff')
            WHERE converted_booking_id IS NOT NULL
              AND booking_status <> 'converted'
            """
        )
    )
    _ensure_guest_notification_outbox(db)
    _ensure_payment_requests_table(db)
    db.commit()


def _row_to_dict(row) -> dict:
    return dict(row._mapping)


def _record_public_request_conversion_denied(
    db: Session,
    *,
    request_id: int,
    request_data: dict,
    user_email: str | None,
    reason: str,
    role_key: str | None = None,
) -> None:
    record_audit_log(
        db,
        action="public_request_conversion_blocked_unauthorized",
        entity_type="public_booking_request",
        entity_id=request_id,
        property_code=request_data.get("property_code"),
        business_date=request_data.get("check_in_date"),
        performed_by=(user_email or "unknown_user"),
        details={
            "reason": reason,
            "role_key": role_key,
            "permission": PUBLIC_REQUEST_CONVERT_PERMISSION,
            "guest_name": request_data.get("guest_name"),
            "booking_status": request_data.get("booking_status"),
            "converted_booking_id": request_data.get("converted_booking_id"),
        },
    )
    record_pms_audit_log(
        db,
        property_code=request_data.get("property_code"),
        user_email=user_email,
        module="booking_hub",
        action="public_request_conversion_blocked_unauthorized",
        record_type="public_booking_request",
        record_id=request_id,
        old_value={
            "booking_status": request_data.get("booking_status"),
            "converted_booking_id": request_data.get("converted_booking_id"),
        },
        new_value={
            "reason": reason,
            "role_key": role_key,
            "permission": PUBLIC_REQUEST_CONVERT_PERMISSION,
        },
    )


def _require_public_request_conversion_permission(
    db: Session,
    *,
    request_id: int,
    request_data: dict,
    user_email: str | None,
) -> dict:
    try:
        actor = require_pms_permission(
            db,
            permission_key=PUBLIC_REQUEST_CONVERT_PERMISSION,
            property_code=request_data["property_code"],
            user_email=user_email,
        )
    except HTTPException as exc:
        _record_public_request_conversion_denied(
            db,
            request_id=request_id,
            request_data=request_data,
            user_email=user_email,
            reason=f"permission_check_failed:{exc.status_code}",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PUBLIC_REQUEST_CONVERT_DENIED_MESSAGE,
        ) from exc

    role_key = str(actor.get("role_key") or "").strip().lower()
    if role_key not in PUBLIC_REQUEST_CONVERT_ROLE_KEYS:
        _record_public_request_conversion_denied(
            db,
            request_id=request_id,
            request_data=request_data,
            user_email=actor.get("email") or user_email,
            reason="role_not_allowed_for_conversion",
            role_key=role_key,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PUBLIC_REQUEST_CONVERT_DENIED_MESSAGE,
        )

    return actor


def _get_hotel_id(db: Session, property_code: str) -> int:
    row = db.execute(
        text("SELECT id FROM hotels WHERE property_code = :property_code LIMIT 1"),
        {"property_code": property_code},
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hotel found for property_code={property_code}",
        )
    return int(row[0])


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_name = :table_name
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
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _ensure_folios_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS folios (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                booking_id INTEGER NOT NULL,
                guest_name VARCHAR(150) NOT NULL,
                currency VARCHAR(10) DEFAULT 'ETB',
                status VARCHAR(50) DEFAULT 'open',
                total_charges NUMERIC(12, 2) DEFAULT 0,
                total_payments NUMERIC(12, 2) DEFAULT 0,
                balance NUMERIC(12, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("ALTER TABLE folios ADD COLUMN IF NOT EXISTS total_charges NUMERIC(12, 2) DEFAULT 0"))
    db.execute(text("ALTER TABLE folios ADD COLUMN IF NOT EXISTS total_payments NUMERIC(12, 2) DEFAULT 0"))
    db.execute(text("ALTER TABLE folios ADD COLUMN IF NOT EXISTS balance NUMERIC(12, 2) DEFAULT 0"))
    db.execute(text("ALTER TABLE folios ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open'"))


def _ensure_folio_transactions_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS folio_transactions (
                id SERIAL PRIMARY KEY,
                folio_id INTEGER NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                txn_type VARCHAR(50) NOT NULL,
                category VARCHAR(80) NOT NULL,
                description TEXT,
                amount NUMERIC(12, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'ETB',
                booking_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS reference VARCHAR(160)"))


def _refresh_folio_totals(db: Session, folio_id: int) -> None:
    _ensure_folio_transactions_table(db)
    row = db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN txn_type = 'charge' THEN amount ELSE 0 END), 0) AS total_charges,
              COALESCE(SUM(CASE WHEN txn_type = 'payment' THEN amount ELSE 0 END), 0) AS total_payments
            FROM folio_transactions
            WHERE folio_id = :folio_id
            """
        ),
        {"folio_id": folio_id},
    ).mappings().first()
    total_charges = Decimal(str(row["total_charges"] if row else 0))
    total_payments = Decimal(str(row["total_payments"] if row else 0))
    db.execute(
        text(
            """
            UPDATE folios
            SET total_charges = :total_charges,
                total_payments = :total_payments,
                balance = :balance
            WHERE id = :folio_id
            """
        ),
        {
            "folio_id": folio_id,
            "total_charges": total_charges,
            "total_payments": total_payments,
            "balance": total_charges - total_payments,
        },
    )


def _get_or_create_pending_folio(
    db: Session,
    *,
    property_code: str,
    booking_id: int,
    guest_name: str,
    currency: str = "ETB",
) -> int:
    _ensure_folios_table(db)
    existing = db.execute(
        text(
            """
            SELECT id
            FROM folios
            WHERE property_code = :property_code
              AND booking_id = :booking_id
              AND COALESCE(status, 'open') = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).first()
    if existing:
        return int(existing[0])

    created = db.execute(
        text(
            """
            INSERT INTO folios (
                property_code,
                booking_id,
                guest_name,
                currency,
                status,
                total_charges,
                total_payments,
                balance
            )
            VALUES (
                :property_code,
                :booking_id,
                :guest_name,
                :currency,
                'open',
                0,
                0,
                0
            )
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "booking_id": booking_id,
            "guest_name": guest_name or "Guest",
            "currency": currency,
        },
    ).first()
    return int(created[0])


def _generate_confirmation_id(property_code: str) -> str:
    return f"GZ-{property_code}-{datetime.now().strftime('%Y%m%d-%H%M')}"


def _deposit_link_from_token(token: str) -> str:
    return f"/public/deposit/{token}"


def _estimate_public_request_value(request_data: dict, db: Session | None = None) -> float:
    quote = _quote_for_request(request_data, db=db)
    return float(quote["total_etb"])


def _estimate_deposit_amount(request_data: dict, db: Session | None = None) -> float:
    quote = _quote_for_request(request_data, db=db)
    return float(quote["deposit_required_etb"])


def _quote_for_request(request_data: dict, rate_code: str = "BAR", db: Session | None = None) -> dict:
    return quote_stay(
        property_code=request_data["property_code"],
        check_in=request_data["check_in_date"],
        check_out=request_data["check_out_date"],
        room_type=request_data.get("room_type"),
        rooms=1,
        adults=int(request_data.get("adults") or 1),
        children=int(request_data.get("children") or 0),
        rate_code=rate_code,
        db=db,
    )


def _ensure_payment_requests_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS payment_requests (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                public_request_id INTEGER,
                booking_id INTEGER,
                guest_name VARCHAR(150),
                guest_email VARCHAR(150),
                guest_phone VARCHAR(50),
                amount_etb NUMERIC(12, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'ETB',
                token VARCHAR(160) UNIQUE NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                expires_at TIMESTAMP,
                created_by VARCHAR(150) DEFAULT 'booking_hub_staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS property_code VARCHAR(20)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS public_request_id INTEGER"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS booking_id INTEGER"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_name VARCHAR(150)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_email VARCHAR(150)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(50)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS amount_etb NUMERIC(12, 2) DEFAULT 0"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ETB'"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS token VARCHAR(160)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS created_by VARCHAR(150) DEFAULT 'booking_hub_staff'"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider VARCHAR(80)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider_reference VARCHAR(160)"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_id INTEGER"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_transaction_id INTEGER"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failed_at TIMESTAMP"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failure_reason TEXT"))
    db.execute(text("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"))
    db.execute(text("ALTER TABLE payment_requests ALTER COLUMN booking_id DROP NOT NULL"))
    db.execute(text("ALTER TABLE payment_requests ALTER COLUMN token DROP NOT NULL"))
    db.execute(text("UPDATE payment_requests SET currency = COALESCE(currency, 'ETB')"))
    db.execute(text("UPDATE payment_requests SET status = COALESCE(status, 'pending')"))
    db.execute(text("UPDATE payment_requests SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"))
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_requests_token_unique
            ON payment_requests (token)
            WHERE token IS NOT NULL
            """
        )
    )


def _ensure_guest_notification_outbox(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER,
                public_request_id INTEGER,
                property_code VARCHAR(50) NOT NULL,
                channel VARCHAR(50) NOT NULL,
                recipient TEXT,
                action VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                business_date DATE,
                status VARCHAR(50) NOT NULL DEFAULT 'queued',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)"))
    db.execute(text("ALTER TABLE guest_notification_outbox ALTER COLUMN booking_id DROP NOT NULL"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0"))
    db.execute(text("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ"))
    db.execute(text("UPDATE guest_notification_outbox SET attempt_count = COALESCE(attempt_count, 0)"))
    db.execute(text("UPDATE guest_notification_outbox SET retry_count = COALESCE(retry_count, attempt_count, 0)"))
    db.execute(text("UPDATE guest_notification_outbox SET status = 'skipped' WHERE status = 'pending_contact_review'"))


def _queue_guest_notification(
    db: Session,
    *,
    property_code: str,
    public_request_id: int,
    booking_id: Optional[int],
    guest_email: Optional[str],
    guest_phone: Optional[str],
    channel: Optional[str],
    action: str,
    message: str,
    business_date: date,
    guest_profile: Optional[dict] = None,
) -> str:
    _ensure_guest_notification_outbox(db)
    delivery_channel = "email" if guest_email else "sms" if guest_phone else channel or "staff_followup"
    recipient = guest_email or guest_phone
    status_value = "queued" if recipient else "skipped"
    db.execute(
        text(
            """
            INSERT INTO guest_notification_outbox (
                booking_id,
                public_request_id,
                guest_profile_id,
                guest_id,
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
                :public_request_id,
                :guest_profile_id,
                :guest_id,
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
            "public_request_id": public_request_id,
            "guest_profile_id": guest_profile.get("id") if guest_profile else None,
            "guest_id": guest_profile.get("guest_id") if guest_profile else None,
            "property_code": property_code,
            "channel": delivery_channel,
            "recipient": recipient,
            "action": action,
            "message": message,
            "business_date": business_date,
            "status": status_value,
        },
    )
    return status_value


def _create_deposit_payment_request(
    db: Session,
    *,
    request_data: dict,
    amount_etb: float = 0,
) -> str:
    _ensure_payment_requests_table(db)
    existing = db.execute(
        text(
            """
            SELECT token
            FROM payment_requests
            WHERE public_request_id = :request_id
              AND status IN ('pending', 'sent')
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"request_id": request_data["id"]},
    ).first()
    if existing:
        return _deposit_link_from_token(existing[0])

    token = token_urlsafe(32)
    db.execute(
        text(
            """
            INSERT INTO payment_requests (
                property_code,
                public_request_id,
                guest_name,
                guest_email,
                guest_phone,
                amount_etb,
                currency,
                token,
                status,
                expires_at
            )
            VALUES (
                :property_code,
                :public_request_id,
                :guest_name,
                :guest_email,
                :guest_phone,
                :amount_etb,
                'ETB',
                :token,
                'sent',
                :expires_at
            )
            """
        ),
        {
            "property_code": request_data["property_code"],
            "public_request_id": request_data["id"],
            "guest_name": request_data["guest_name"],
            "guest_email": request_data.get("guest_email"),
            "guest_phone": request_data.get("guest_phone"),
            "amount_etb": amount_etb,
            "token": token,
            "expires_at": datetime.utcnow() + timedelta(days=3),
        },
    )
    return _deposit_link_from_token(token)


def _validate_payment_webhook_secret(secret: Optional[str]) -> None:
    expected = os.getenv("GUZO_PAYMENT_WEBHOOK_SECRET") or os.getenv("PAYMENT_WEBHOOK_SECRET")
    if expected and secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payment webhook secret")


def _booking_columns(db: Session) -> set[str]:
    return _table_columns(db, "bookings")


def _update_booking_after_deposit(db: Session, *, booking_id: int, property_code: str) -> None:
    columns = _booking_columns(db)
    assignments = []
    if "payment_status" in columns:
        assignments.append("payment_status = 'deposit_paid'")
    if "guarantee_type" in columns:
        assignments.append("guarantee_type = 'guaranteed'")
    if not assignments:
        return
    db.execute(
        text(
            f"""
            UPDATE bookings
            SET {", ".join(assignments)}
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {"booking_id": booking_id, "property_code": property_code},
    )


def _post_deposit_to_folio(
    db: Session,
    *,
    property_code: str,
    booking_id: int,
    guest_name: str,
    amount: Decimal,
    currency: str,
    provider: str,
    provider_reference: Optional[str],
    business_date: date,
    payment_request_id: int,
) -> tuple[int, int | None]:
    request = request_deposit(
        db,
        property_code=property_code,
        booking_id=booking_id,
        business_date=business_date,
        required_amount=amount,
        requested_amount=amount,
        currency=currency,
        refundable=True,
        actor="payment_webhook",
        idempotency_key=f"deposit-request:{payment_request_id}",
        reference=provider_reference,
    )
    receipt = receive_deposit(
        db,
        property_code=property_code,
        account_id=int(request["id"]),
        business_date=business_date,
        amount=amount,
        payment_method=provider,
        reference=provider_reference or f"payment-request-{payment_request_id}",
        actor="payment_webhook",
        idempotency_key=f"deposit:{payment_request_id}",
    )
    allocated = allocate_deposit(
        db,
        property_code=property_code,
        account_id=int(request["id"]),
        amount=amount,
        actor="payment_webhook",
        idempotency_key=f"deposit-allocation:{payment_request_id}",
    )
    db.execute(
        text("UPDATE payment_requests SET deposit_account_id=:account_id WHERE id=:payment_request_id AND property_code=:property_code"),
        {"account_id": request["id"], "payment_request_id": payment_request_id, "property_code": property_code},
    )
    return int(allocated["folio_id"]), None

    # Legacy implementation retained below for migration readability; lifecycle return above is authoritative.
    _ensure_folios_table(db)
    _ensure_folio_transactions_table(db)
    folio_id = _get_or_create_pending_folio(
        db,
        property_code=property_code,
        booking_id=booking_id,
        guest_name=guest_name,
        currency=currency,
    )
    txn = db.execute(
        text(
            """
            INSERT INTO folio_transactions (
                folio_id,
                property_code,
                business_date,
                txn_type,
                category,
                description,
                amount,
                currency,
                booking_id,
                reference
            )
            VALUES (
                :folio_id,
                :property_code,
                :business_date,
                'payment',
                :category,
                :description,
                :amount,
                :currency,
                :booking_id,
                :reference
            )
            RETURNING id
            """
        ),
        {
            "folio_id": folio_id,
            "property_code": property_code,
            "business_date": business_date,
            "category": provider,
            "description": f"Deposit payment: {provider_reference or 'provider confirmation'}",
            "amount": amount,
            "currency": currency,
            "booking_id": booking_id,
            "reference": f"deposit:{payment_request_id}",
        },
    ).first()
    post_finance_transaction(
        db,
        property_code=property_code,
        business_date=business_date,
        folio_id=folio_id,
        booking_id=booking_id,
        transaction_type="deposit",
        amount=amount,
        currency=currency,
        direction="credit",
        payment_method=provider,
        reference=provider_reference,
        source_document_type="payment_request",
        source_document_id=payment_request_id,
        created_by="payment_webhook",
        idempotency_key=f"deposit:{payment_request_id}",
    )
    _refresh_folio_totals(db, folio_id)
    return folio_id, int(txn[0])


def _post_existing_paid_deposit_for_booking(
    db: Session,
    *,
    request_id: int,
    booking_id: int,
    property_code: str,
    guest_name: str,
    business_date: date,
) -> dict:
    _ensure_payment_requests_table(db)
    payment = db.execute(
        text(
            """
            SELECT *
            FROM payment_requests
            WHERE public_request_id = :request_id
              AND status = 'paid'
              AND folio_transaction_id IS NULL
            ORDER BY paid_at DESC NULLS LAST, id DESC
            LIMIT 1
            FOR UPDATE
            """
        ),
        {"request_id": request_id},
    ).mappings().first()
    if not payment:
        return {"posted": False}

    provider = payment.get("provider") or "deposit"
    provider_reference = payment.get("provider_reference") or f"payment-request-{payment['id']}"
    amount = Decimal(str(payment.get("amount_etb") or 0))
    folio_id, folio_transaction_id = _post_deposit_to_folio(
        db,
        property_code=property_code,
        booking_id=booking_id,
        guest_name=guest_name,
        amount=amount,
        currency=payment.get("currency") or "ETB",
        provider=provider,
        provider_reference=provider_reference,
        business_date=business_date,
        payment_request_id=int(payment["id"]),
    )
    _update_booking_after_deposit(db, booking_id=booking_id, property_code=property_code)
    db.execute(
        text(
            """
            UPDATE payment_requests
            SET booking_id = :booking_id,
                folio_id = :folio_id,
                folio_transaction_id = :folio_transaction_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :payment_request_id
            """
        ),
        {
            "payment_request_id": payment["id"],
            "booking_id": booking_id,
            "folio_id": folio_id,
            "folio_transaction_id": folio_transaction_id,
        },
    )
    return {
        "posted": True,
        "payment_request_id": payment["id"],
        "folio_id": folio_id,
        "folio_transaction_id": folio_transaction_id,
        "amount_etb": str(amount),
    }


def _latest_request_handoff(db: Session, request_id: int) -> dict:
    row = db.execute(
        text(
            """
            SELECT
              b.confirmation_id,
              n.status AS guest_notification_status,
              pr.token AS deposit_token
            FROM public_booking_requests p
            LEFT JOIN bookings b ON b.id = p.converted_booking_id
            LEFT JOIN LATERAL (
              SELECT status
              FROM guest_notification_outbox
              WHERE public_request_id = p.id
              ORDER BY id DESC
              LIMIT 1
            ) n ON TRUE
            LEFT JOIN LATERAL (
              SELECT token
              FROM payment_requests
              WHERE public_request_id = p.id
                AND status IN ('pending', 'sent')
              ORDER BY id DESC
              LIMIT 1
            ) pr ON TRUE
            WHERE p.id = :request_id
            """
        ),
        {"request_id": request_id},
    ).mappings().first()
    if not row:
        return {}
    return {
        "confirmation_id": row["confirmation_id"],
        "guest_notification_status": row["guest_notification_status"],
        "deposit_payment_link": _deposit_link_from_token(row["deposit_token"]) if row["deposit_token"] else None,
    }


def _room_status_expression(columns: set[str]) -> str:
    if "hk_status" in columns:
        return "hk_status"
    if "housekeeping_status" in columns:
        return "housekeeping_status"
    if "status" in columns:
        return "status"
    return "'clean'"


def _normalize_requested_room_type(value: Optional[str]) -> Optional[str]:
    room_type = str(value or "").strip()
    if not room_type or room_type.upper() == "TBD":
        return None
    return room_type


def _availability_for_request(db: Session, request_data: dict, rooms_requested: int = 1) -> dict:
    property_code = request_data["property_code"]
    check_in = request_data["check_in_date"]
    check_out = request_data["check_out_date"]
    requested_room_type = _normalize_requested_room_type(request_data.get("room_type"))
    room_columns = _table_columns(db, "rooms")
    booking_columns = _table_columns(db, "bookings")
    status_expr = _room_status_expression(room_columns)
    active_filter = "AND (is_active IS NULL OR is_active = TRUE)" if "is_active" in room_columns else ""
    room_type_filter = ""
    booking_room_type_filter = ""
    params = {"property_code": property_code, "room_type": requested_room_type}
    if requested_room_type and "room_type" in room_columns:
        room_type_filter = "AND LOWER(COALESCE(room_type, '')) = LOWER(:room_type)"
    if requested_room_type and "room_type" in booking_columns:
        booking_room_type_filter = "AND LOWER(COALESCE(room_type, '')) = LOWER(:room_type)"
    booking_rooms_expr = "COALESCE(rooms, 1)" if "rooms" in booking_columns else "1"

    total_rooms = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM rooms
                WHERE property_code = :property_code
                  {active_filter}
                  {room_type_filter}
                """
            ),
            params,
        ).scalar()
        or 0
    )

    daily = []
    current = check_in
    while current < check_out:
        overlap = int(
            db.execute(
                text(
                    f"""
                    SELECT COALESCE(SUM({booking_rooms_expr}), 0)
                    FROM bookings
                    WHERE property_code = :property_code
                      AND LOWER(COALESCE(booking_status, '')) IN (
                        'confirmed',
                        'reserved',
                        'pending_guarantee',
                        'in_house',
                        'checked_in'
                      )
                      AND check_in_date <= :stay_date
                      AND check_out_date > :stay_date
                      {booking_room_type_filter}
                    """
                ),
                {**params, "stay_date": current},
            ).scalar()
            or 0
        )
        out_of_order = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM rooms
                    WHERE property_code = :property_code
                      {active_filter}
                      {room_type_filter}
                      AND LOWER(COALESCE({status_expr}, '')) IN (
                        'out_of_order',
                        'out of order',
                        'out_of_service',
                        'out of service',
                        'maintenance',
                        'service_in_progress',
                        'service in progress',
                        'ooo'
                      )
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        available = max(total_rooms - overlap - out_of_order, 0)
        daily.append(
            {
                "date": current.isoformat(),
                "total_rooms": total_rooms,
                "overlapping_bookings": overlap,
                "out_of_order_rooms": out_of_order,
                "available_rooms": available,
            }
        )
        current += timedelta(days=1)

    min_available = min((row["available_rooms"] for row in daily), default=0)
    return {
        "room_type": requested_room_type,
        "rooms_requested": rooms_requested,
        "total_rooms": total_rooms,
        "available_rooms": min_available,
        "is_available": total_rooms > 0 and min_available >= rooms_requested,
        "daily_breakdown": daily,
    }


@router.post("/public/booking-request", status_code=status.HTTP_201_CREATED)
def create_public_booking_request(
    payload: PublicBookingRequestCreate,
    db: Session = Depends(get_db),
):
    ensure_public_booking_requests_table(db)
    property_code = payload.property_code.strip().upper()

    result = db.execute(
        text(
            """
            INSERT INTO public_booking_requests (
                property_code,
                source,
                channel,
                guest_name,
                guest_phone,
                guest_email,
                check_in_date,
                check_out_date,
                adults,
                children,
                room_type,
                reservation_type,
                booking_status,
                guarantee_type,
                deposit_status,
                special_requests,
                notes
            )
            VALUES (
                :property_code,
                :source,
                :channel,
                :guest_name,
                :guest_phone,
                :guest_email,
                :check_in_date,
                :check_out_date,
                :adults,
                :children,
                :room_type,
                :reservation_type,
                'pending_request',
                :guarantee_type,
                :deposit_status,
                :special_requests,
                :notes
            )
            RETURNING *
            """
        ),
        {
            "property_code": property_code,
            "source": payload.source or "chatbot",
            "channel": payload.channel,
            "guest_name": payload.guest_name.strip(),
            "guest_phone": payload.guest_phone,
            "guest_email": payload.guest_email,
            "check_in_date": payload.check_in_date,
            "check_out_date": payload.check_out_date,
            "adults": payload.adults,
            "children": payload.children,
            "room_type": payload.room_type,
            "reservation_type": payload.reservation_type,
            "guarantee_type": payload.guarantee_type,
            "deposit_status": payload.deposit_status,
            "special_requests": payload.special_requests,
            "notes": payload.notes,
        },
    )
    row = result.first()
    created_request = _row_to_dict(row)
    record_audit_log(
        db,
        action="request_created",
        entity_type="public_booking_request",
        entity_id=created_request["id"],
        property_code=property_code,
        business_date=payload.check_in_date,
        performed_by="public_guest",
        details={
            "source": payload.source or "chatbot",
            "channel": payload.channel,
            "guest_name": payload.guest_name.strip(),
            "check_in_date": payload.check_in_date.isoformat(),
            "check_out_date": payload.check_out_date.isoformat(),
        },
    )
    db.commit()

    return {
        "status": "success",
        "message": "Your reservation request has been received. Our hotel team will review availability and confirm your booking shortly.",
        "booking_status": "pending_request",
        "request": created_request,
    }


@router.get("/public/deposit/{token}")
def get_public_deposit_request(
    token: str,
    db: Session = Depends(get_db),
):
    _ensure_payment_requests_table(db)
    row = db.execute(
        text(
            """
            SELECT
              id,
              property_code,
              public_request_id,
              booking_id,
              guest_name,
              amount_etb,
              currency,
              status,
              expires_at,
              created_at
            FROM payment_requests
            WHERE token = :token
            LIMIT 1
            """
        ),
        {"token": token},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit request not found")

    is_expired = bool(row["expires_at"] and row["expires_at"] < datetime.utcnow())
    return {
        "ok": not is_expired and row["status"] in {"pending", "sent"},
        "property_code": row["property_code"],
        "public_request_id": row["public_request_id"],
        "booking_id": row["booking_id"],
        "guest_name": row["guest_name"],
        "amount_etb": float(row["amount_etb"] or 0),
        "currency": row["currency"] or "ETB",
        "status": "expired" if is_expired else row["status"],
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        "message": "Use the hotel's secure payment provider page. Do not send card details by chat.",
    }


@router.post("/public/deposit/webhook")
def complete_deposit_payment_webhook(
    payload: DepositPaymentWebhook,
    db: Session = Depends(get_db),
    x_payment_webhook_secret: Optional[str] = Header(None),
):
    _validate_payment_webhook_secret(x_payment_webhook_secret)
    _ensure_payment_requests_table(db)
    _ensure_guest_notification_outbox(db)

    normalized_status = payload.status.strip().lower()
    if normalized_status not in {"paid", "success", "succeeded", "failed", "expired"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment status")

    payment_row = db.execute(
        text(
            """
            SELECT *
            FROM payment_requests
            WHERE token = :token
            LIMIT 1
            FOR UPDATE
            """
        ),
        {"token": payload.token},
    ).mappings().first()
    if not payment_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment request not found")

    payment = dict(payment_row)
    if payment.get("expires_at") and payment["expires_at"] < datetime.utcnow() and normalized_status not in {"paid", "success", "succeeded"}:
        normalized_status = "expired"

    if payment.get("status") == "paid" and payment.get("folio_transaction_id"):
        return {
            "ok": True,
            "idempotent": True,
            "status": "paid",
            "payment_request_id": payment["id"],
            "folio_id": payment.get("folio_id"),
            "folio_transaction_id": payment.get("folio_transaction_id"),
            "message": "Deposit payment was already posted.",
        }

    provider = payload.provider.strip().lower() or "payment_provider"
    provider_reference = payload.provider_reference or f"payment-request-{payment['id']}"
    amount = Decimal(str(payload.amount_etb if payload.amount_etb is not None else payment.get("amount_etb") or 0))
    currency = payment.get("currency") or "ETB"
    public_request_id = payment.get("public_request_id")
    request_data = None
    if public_request_id:
        request_row = db.execute(
            text("SELECT * FROM public_booking_requests WHERE id = :request_id LIMIT 1"),
            {"request_id": public_request_id},
        ).mappings().first()
        request_data = dict(request_row) if request_row else None

    booking_id = payment.get("booking_id") or (request_data or {}).get("converted_booking_id")
    property_code = payment["property_code"]
    guest_name = payment.get("guest_name") or (request_data or {}).get("guest_name") or "Guest"
    business_date = (request_data or {}).get("check_in_date") or date.today()

    if normalized_status in {"failed", "expired"}:
        db.execute(
            text(
                """
                UPDATE payment_requests
                SET status = :status,
                    provider = :provider,
                    provider_reference = :provider_reference,
                    failure_reason = :failure_reason,
                    failed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :payment_request_id
                """
            ),
            {
                "payment_request_id": payment["id"],
                "status": normalized_status,
                "provider": provider,
                "provider_reference": provider_reference,
                "failure_reason": payload.failure_reason,
            },
        )
        record_audit_log(
            db,
            action=f"deposit_payment_{normalized_status}",
            entity_type="payment_request",
            entity_id=payment["id"],
            property_code=property_code,
            business_date=business_date,
            payment_request_id=int(payment["id"]),
            performed_by="payment_webhook",
            details={
                "provider": provider,
                "provider_reference": provider_reference,
                "public_request_id": public_request_id,
                "booking_id": booking_id,
                "reason": payload.failure_reason,
            },
        )
        db.commit()
        return {
            "ok": normalized_status == "expired",
            "status": normalized_status,
            "payment_request_id": payment["id"],
            "message": f"Deposit payment marked {normalized_status}.",
        }

    folio_id = None
    folio_transaction_id = None
    if booking_id:
        folio_id, folio_transaction_id = _post_deposit_to_folio(
            db,
            property_code=property_code,
            booking_id=int(booking_id),
            guest_name=guest_name,
            amount=amount,
            currency=currency,
            provider=provider,
            provider_reference=provider_reference,
            business_date=business_date,
        )
        _update_booking_after_deposit(db, booking_id=int(booking_id), property_code=property_code)

    db.execute(
        text(
            """
            UPDATE payment_requests
            SET status = 'paid',
                provider = :provider,
                provider_reference = :provider_reference,
                amount_etb = :amount_etb,
                booking_id = COALESCE(booking_id, :booking_id),
                folio_id = :folio_id,
                folio_transaction_id = :folio_transaction_id,
                paid_at = COALESCE(:paid_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :payment_request_id
            """
        ),
        {
            "payment_request_id": payment["id"],
            "provider": provider,
            "provider_reference": provider_reference,
            "amount_etb": amount,
            "booking_id": booking_id,
            "folio_id": folio_id,
            "folio_transaction_id": folio_transaction_id,
            "paid_at": payload.paid_at,
        },
    )

    if public_request_id:
        db.execute(
            text(
                """
                UPDATE public_booking_requests
                SET deposit_status = 'paid',
                    guarantee_type = 'guaranteed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :request_id
                """
            ),
            {"request_id": public_request_id},
        )

    receipt_message = (
        f"Dear {guest_name}, your deposit payment of ETB {amount:,.2f} was received. "
        f"Reference: {provider_reference}. "
        "Thank you. Your hotel reservation guarantee is now recorded."
    )
    _queue_guest_notification(
        db,
        property_code=property_code,
        public_request_id=public_request_id or 0,
        booking_id=int(booking_id) if booking_id else None,
        guest_email=payment.get("guest_email") or (request_data or {}).get("guest_email"),
        guest_phone=payment.get("guest_phone") or (request_data or {}).get("guest_phone"),
        channel=(request_data or {}).get("channel") or (request_data or {}).get("source"),
        action="deposit_receipt",
        message=receipt_message,
        business_date=business_date,
    )
    record_audit_log(
        db,
        action="deposit_payment_completed",
        entity_type="payment_request",
        entity_id=payment["id"],
        property_code=property_code,
        business_date=business_date,
        performed_by="payment_webhook",
        details={
            "provider": provider,
            "provider_reference": provider_reference,
            "public_request_id": public_request_id,
            "booking_id": booking_id,
            "folio_id": folio_id,
            "folio_transaction_id": folio_transaction_id,
            "amount_etb": str(amount),
            "posted_to_folio": bool(folio_transaction_id),
        },
    )
    db.commit()

    return {
        "ok": True,
        "status": "paid",
        "payment_request_id": payment["id"],
        "booking_id": booking_id,
        "folio_id": folio_id,
        "folio_transaction_id": folio_transaction_id,
        "posted_to_folio": bool(folio_transaction_id),
        "message": "Deposit payment completed and folio posting handled.",
    }


@router.get("/booking-hub/public-requests", response_model=list[PublicBookingRequestOut])
def list_public_booking_requests(
    property_code: str = Query(..., min_length=1),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_public_booking_requests_table(db)
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    clauses = ["p.property_code = :property_code"]
    params = {"property_code": property_code}

    if status_filter:
        clauses.append("p.booking_status = :status_filter")
        params["status_filter"] = status_filter

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        text(
            f"""
            SELECT
              p.*,
              b.confirmation_id,
              n.status AS guest_notification_status,
              pr.token AS deposit_token
            FROM public_booking_requests p
            LEFT JOIN bookings b ON b.id = p.converted_booking_id
            LEFT JOIN LATERAL (
              SELECT status
              FROM guest_notification_outbox
              WHERE public_request_id = p.id
              ORDER BY id DESC
              LIMIT 1
            ) n ON TRUE
            LEFT JOIN LATERAL (
              SELECT token
              FROM payment_requests
              WHERE public_request_id = p.id
                AND status IN ('pending', 'sent')
              ORDER BY id DESC
              LIMIT 1
            ) pr ON TRUE
            {where_sql}
            ORDER BY p.created_at DESC, p.id DESC
            """
        ),
        params,
    ).all()
    result = []
    for row in rows:
        item = _row_to_dict(row)
        token = item.pop("deposit_token", None)
        item["deposit_payment_link"] = _deposit_link_from_token(token) if token else None
        result.append(item)
    return result


@router.patch("/booking-hub/public-requests/{request_id}/status", response_model=PublicBookingRequestOut)
def update_public_booking_request_status(
    request_id: int,
    payload: PublicBookingRequestStatusUpdate,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_public_booking_requests_table(db)
    if payload.status not in REQUEST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported public booking request status: {payload.status}",
        )

    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    current_row = db.execute(
        text("SELECT * FROM public_booking_requests WHERE id = :request_id AND property_code = :property_code"),
        {"request_id": request_id, "property_code": property_code},
    ).first()
    if not current_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public booking request not found")

    current = _row_to_dict(current_row)
    permission_key = (
        "booking.request_deposit"
        if payload.status in {"deposit_requested", "deposit_required"}
        else "booking.reject_public_request"
        if payload.status == "rejected"
        else "booking.review_public_request"
    )
    actor = require_pms_permission(
        db,
        permission_key=permission_key,
        property_code=current["property_code"],
        user_email=x_pms_user_email,
    )
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=current["property_code"],
        guest_name=current["guest_name"],
        email=current.get("guest_email"),
        phone=current.get("guest_phone"),
        preferences={
            "room_type": current.get("room_type"),
            "source": current.get("source"),
            "channel": current.get("channel"),
            "special_requests": current.get("special_requests"),
        },
        notes=current.get("notes"),
    )
    link_guest_profile_to_public_request(db, request_id=request_id, guest_profile=guest_profile)
    if current.get("converted_booking_id") and payload.status != "converted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Converted requests cannot be changed. View the linked PMS booking instead.",
        )

    deposit_status_sql = """
                deposit_status = CASE
                    WHEN :booking_status IN ('deposit_requested', 'deposit_required') THEN 'requested'
                    ELSE deposit_status
                END,
    """

    deposit_link = None
    if payload.status in {"deposit_requested", "deposit_required"}:
        deposit_amount = _estimate_deposit_amount(current, db=db)
        deposit_link = _create_deposit_payment_request(db, request_data=current, amount_etb=deposit_amount)
        notification_message = (
            f"Dear {current['guest_name']}, our Reservations team reviewed your request. "
            f"A deposit of ETB {deposit_amount:,.2f} is required to secure the booking. "
            f"Please use this secure hotel payment request: {deposit_link}. "
            "Do not send card details by chat."
        )
        _queue_guest_notification(
            db,
            property_code=current["property_code"],
            public_request_id=request_id,
            booking_id=current.get("converted_booking_id"),
            guest_email=current.get("guest_email"),
            guest_phone=current.get("guest_phone"),
            channel=current.get("channel") or current.get("source"),
            action="deposit_requested",
            message=notification_message,
            business_date=current["check_in_date"],
            guest_profile=guest_profile,
        )

    row = db.execute(
        text(
            f"""
            UPDATE public_booking_requests
            SET booking_status = :booking_status,
                {deposit_status_sql}
                notes = COALESCE(:notes, notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :request_id AND property_code = :property_code
            RETURNING *
            """
        ),
        {
            "request_id": request_id,
            "property_code": property_code,
            "booking_status": payload.status,
            "notes": payload.notes,
        },
    ).first()

    updated = _row_to_dict(row)
    updated.update(_latest_request_handoff(db, request_id))
    record_audit_log(
        db,
        action=f"request_{payload.status}",
        entity_type="public_booking_request",
        entity_id=request_id,
        property_code=updated["property_code"],
        business_date=updated["check_in_date"],
        performed_by="booking_hub_staff",
        details={
            "old_status": current.get("booking_status"),
            "new_status": payload.status,
            "notes": payload.notes,
            "deposit_payment_link": deposit_link,
        },
    )
    record_pms_audit_log(
        db,
        property_code=updated["property_code"],
        user_email=actor["email"],
        module="booking_hub",
        action=f"public_request_{payload.status}",
        record_type="public_booking_request",
        record_id=request_id,
        old_value={"booking_status": current.get("booking_status")},
        new_value={
            "booking_status": payload.status,
            "deposit_payment_link": deposit_link,
            "permission": permission_key,
        },
    )
    db.commit()
    return updated


@router.post("/booking-hub/public-requests/{request_id}/convert")
def convert_public_booking_request(
    request_id: int,
    payload: PublicBookingRequestConvert,
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    ensure_public_booking_requests_table(db)
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    request_row = db.execute(
        text("SELECT * FROM public_booking_requests WHERE id = :request_id AND property_code = :property_code"),
        {"request_id": request_id, "property_code": property_code},
    ).first()

    if not request_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public booking request not found")

    request_data = _row_to_dict(request_row)
    actor = _require_public_request_conversion_permission(
        db,
        request_id=request_id,
        request_data=request_data,
        user_email=x_pms_user_email,
    )
    if request_data.get("converted_booking_id") or str(request_data.get("booking_status") or "").lower() == "converted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is already converted")
    if request_data.get("booking_status") == "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejected requests cannot be converted")

    availability = _availability_for_request(db, request_data, rooms_requested=1)
    if not availability["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Requested room type is not available for the full stay. Review alternate dates, alternate room type, waitlist, or manager-approved overbooking.",
                "availability": availability,
            },
        )

    property_code = request_data["property_code"]
    hotel_id = _get_hotel_id(db, property_code)
    check_in = request_data["check_in_date"]
    check_out = request_data["check_out_date"]
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=request_data["guest_name"],
        email=request_data.get("guest_email"),
        phone=request_data.get("guest_phone"),
        preferences={
            "room_type": request_data.get("room_type"),
            "source": request_data.get("source"),
            "channel": request_data.get("channel"),
            "special_requests": request_data.get("special_requests"),
        },
        notes=request_data.get("notes"),
    )
    link_guest_profile_to_public_request(db, request_id=request_id, guest_profile=guest_profile)
    nights = max((check_out - check_in).days, 1)
    quote = _quote_for_request(request_data, db=db)
    total_amount = payload.total_amount_etb or quote["total_etb"]
    rate_per_night = payload.rate_per_night_etb or quote["nightly_rate_etb"]
    room_type = payload.room_type or request_data.get("room_type")
    channel = request_data.get("channel")
    source = channel or request_data.get("source") or "public_booking_request"
    guarantee_warning = None
    deposit_status = str(request_data.get("deposit_status") or "").lower()
    payment_status = str(payload.payment_status or "").lower()
    if quote.get("guarantee_required") and payment_status not in {"paid", "deposit_paid", "guaranteed", "card_guaranteed", "city_ledger"}:
        guarantee_warning = "Deposit or approved guarantee is missing. Reservation is confirmed but remains pending guarantee review."
    notes = " | ".join(
        part
        for part in [
            f"Converted from public_booking_request #{request_id}",
            f"Source: {request_data.get('source')}" if request_data.get("source") else None,
            f"Channel: {channel}" if channel else None,
            f"Availability Checked: {availability['available_rooms']} available for {availability.get('room_type') or 'house'}",
            f"Rate Quote: {quote['rate_code']} {quote['rate_label']}",
            f"Net Revenue: ETB {quote['net_revenue_etb']:,.2f}",
            f"Service Charge: ETB {quote['service_charge_etb']:,.2f}",
            f"Tax: ETB {quote['tax_etb']:,.2f}",
            f"Deposit Required: ETB {quote['deposit_required_etb']:,.2f}",
            f"Guarantee Warning: {guarantee_warning}" if guarantee_warning else None,
            f"Public Request Deposit Status: {deposit_status}" if deposit_status else None,
            f"Phone: {request_data.get('guest_phone')}" if request_data.get("guest_phone") else None,
            f"Adults: {request_data.get('adults')}",
            f"Children: {request_data.get('children')}",
            f"Special Requests: {request_data.get('special_requests')}" if request_data.get("special_requests") else None,
            payload.notes,
            request_data.get("notes"),
        ]
        if part
    )

    booking_row = db.execute(
        text(
            """
            INSERT INTO bookings (
                confirmation_id,
                hotel_id,
                guest_name,
                guest_email,
                check_in_date,
                check_out_date,
                nights,
                room_type,
                rate_per_night_etb,
                total_revenue_etb,
                payment_method,
                booking_status,
                payment_status,
                source,
                property_code,
                notes,
                created_at
            )
            VALUES (
                :confirmation_id,
                :hotel_id,
                :guest_name,
                :guest_email,
                :check_in_date,
                :check_out_date,
                :nights,
                :room_type,
                :rate_per_night_etb,
                :total_revenue_etb,
                :payment_method,
                'confirmed',
                :payment_status,
                :source,
                :property_code,
                :notes,
                CURRENT_TIMESTAMP
            )
            RETURNING id, confirmation_id
            """
        ),
        {
            "confirmation_id": _generate_confirmation_id(property_code),
            "hotel_id": hotel_id,
            "guest_name": request_data["guest_name"],
            "guest_email": request_data.get("guest_email"),
            "check_in_date": check_in,
            "check_out_date": check_out,
            "nights": nights,
            "room_type": room_type,
            "rate_per_night_etb": rate_per_night,
            "total_revenue_etb": total_amount,
            "payment_method": payload.payment_method,
            "payment_status": payload.payment_status,
            "source": source,
            "property_code": property_code,
            "notes": notes,
        },
    ).first()

    booking_id = int(booking_row[0])
    confirmation_id = booking_row[1]
    link_guest_profile_to_booking(db, booking_id=booking_id, guest_profile=guest_profile)
    folio_id = _get_or_create_pending_folio(
        db,
        property_code=property_code,
        booking_id=booking_id,
        guest_name=request_data["guest_name"],
        currency="ETB",
    )
    link_guest_profile_to_folio(db, folio_id=folio_id, guest_profile=guest_profile)
    deposit_posting = _post_existing_paid_deposit_for_booking(
        db,
        request_id=request_id,
        booking_id=booking_id,
        property_code=property_code,
        guest_name=request_data["guest_name"],
        business_date=check_in,
    )
    if deposit_posting.get("posted"):
        folio_id = int(deposit_posting["folio_id"])
        link_guest_profile_to_folio(db, folio_id=folio_id, guest_profile=guest_profile)
    confirmation_message = (
        f"Dear {request_data['guest_name']}, your booking is confirmed. "
        f"Confirmation Number: {confirmation_id}. "
        f"Stay: {check_in.isoformat()} to {check_out.isoformat()}. "
        f"Room Type: {room_type or 'TBD'}. "
        "Our Front Desk will complete room assignment before check-in."
    )
    notification_status = _queue_guest_notification(
        db,
        property_code=property_code,
        public_request_id=request_id,
        booking_id=booking_id,
        guest_email=request_data.get("guest_email"),
        guest_phone=request_data.get("guest_phone"),
        channel=channel or request_data.get("source"),
        action="booking_confirmation",
        message=confirmation_message,
        business_date=check_in,
        guest_profile=guest_profile,
    )
    if guarantee_warning:
        queue_prearrival_deposit_alert_if_needed(
            db,
            property_code=property_code,
            check_in_date=check_in,
            payment_status=payload.payment_status,
            guest_profile=guest_profile,
            booking_id=booking_id,
            public_request_id=request_id,
        )
    db.execute(
        text(
            """
            UPDATE public_booking_requests
            SET booking_status = 'converted',
                deposit_status = CASE
                    WHEN :payment_status IN ('paid', 'deposit_paid', 'guaranteed') THEN 'paid'
                    ELSE deposit_status
                END,
                converted_booking_id = :booking_id,
                converted_at = CURRENT_TIMESTAMP,
                converted_by = :converted_by,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :request_id
            """
        ),
        {
            "request_id": request_id,
            "booking_id": booking_id,
            "payment_status": payload.payment_status,
            "converted_by": actor["email"],
        },
    )
    record_audit_log(
        db,
        action="request_converted_to_booking",
        entity_type="public_booking_request",
        entity_id=request_id,
        hotel_id=hotel_id,
        property_code=property_code,
        business_date=check_in,
        performed_by="booking_hub_staff",
        details={
            "booking_id": booking_id,
            "confirmation_id": confirmation_id,
            "folio_id": folio_id,
            "deposit_posting": deposit_posting,
            "guest_notification_status": notification_status,
            "old_status": request_data.get("booking_status"),
            "new_status": "converted",
            "guest_name": request_data["guest_name"],
            "payment_status": payload.payment_status,
            "total_amount_etb": payload.total_amount_etb,
            "quoted_total_etb": total_amount,
            "rate_quote": quote,
            "source": request_data.get("source"),
            "channel": channel,
            "availability": availability,
            "guarantee_warning": guarantee_warning,
        },
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="booking_hub",
        action="public_request_converted",
        record_type="public_booking_request",
        record_id=request_id,
        old_value={"booking_status": request_data.get("booking_status")},
        new_value={
            "booking_id": booking_id,
            "confirmation_id": confirmation_id,
            "folio_id": folio_id,
            "source": source,
            "room_type": room_type,
            "total_amount_etb": float(total_amount),
            "guarantee_warning": guarantee_warning,
        },
    )
    db.commit()

    return {
        "ok": True,
        "booking_id": booking_id,
        "confirmation_id": confirmation_id,
        "folio_id": folio_id,
        "deposit_posting": deposit_posting,
        "guest_notification_status": notification_status,
        "availability": availability,
        "guarantee_warning": guarantee_warning,
        "message": f"Public request converted to confirmed booking {confirmation_id}. Open folio #{folio_id} is ready and guest confirmation is {notification_status}.",
    }
