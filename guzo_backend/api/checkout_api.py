from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db, verify_admin_token
from guzo_backend.api.rooms_housekeeping_api import _set_housekeeping_status
from guzo_backend.services.guest_profile_service import (
    find_or_create_guest_profile,
    link_guest_profile_to_booking,
    link_guest_profile_to_folio,
    queue_guest_notification,
)
from guzo_backend.services.finance_transaction_service import post_finance_transaction
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission

router = APIRouter(prefix="/checkout", tags=["Checkout"])

PROPERTY_BASE_CURRENCIES = {
    "DRE001": "ETB",
}

ALLOWED_PAYMENT_METHODS = {
    "cash",
    "card",
    "telebirr",
    "cbebirr",
    "pos",
    "bank_transfer",
    "mobile_money",
}


class CheckoutProcessIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date

    pay_amount: Decimal = Field(Decimal("0"))
    pay_method: str = Field("cash", min_length=1)
    description: str = Field("Checkout Payment", min_length=1)
    currency: str = Field("ETB", min_length=1)
    exchange_rate_to_base: Decimal | None = None
    exchange_rate_source: str | None = None
    exchange_rate_overridden: bool = False
    exchange_rate_override_reason: str | None = None
    idempotency_key: str | None = None

    close_folio: bool = True
    mark_booking_checked_out: bool = True

    @field_validator("pay_method")
    @classmethod
    def validate_pay_method(cls, v: str) -> str:
        m = v.strip().lower()
        if m not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"Unsupported payment method: {v}")
        return m

    @field_validator("property_code")
    @classmethod
    def validate_property_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_code is required")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("currency is required")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        return v or "Checkout Payment"


def _as_decimal(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    return Decimal(str(x))


def _base_currency_for_property(property_code: str) -> str:
    return PROPERTY_BASE_CURRENCIES.get(property_code.strip().upper(), "ETB")


def _payment_exchange_payload(
    *,
    property_code: str,
    original_amount: Decimal,
    original_currency: str,
    exchange_rate_to_base: Decimal | None,
    exchange_rate_source: str | None,
    exchange_rate_overridden: bool,
    exchange_rate_override_reason: str | None,
) -> dict[str, Any]:
    base_currency = _base_currency_for_property(property_code)
    original_currency = original_currency.strip().upper()
    if original_currency == base_currency:
        effective_rate = Decimal("1")
        base_amount = original_amount
        rate_source = exchange_rate_source or "same_currency"
        overridden = False
        override_reason = None
    else:
        if exchange_rate_to_base is None or exchange_rate_to_base <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"exchange_rate_to_base is required when payment currency {original_currency} differs from base currency {base_currency}.",
            )
        effective_rate = exchange_rate_to_base
        base_amount = original_amount * effective_rate
        rate_source = exchange_rate_source or "manual"
        overridden = bool(exchange_rate_overridden)
        override_reason = exchange_rate_override_reason.strip() if exchange_rate_override_reason else None
        if overridden and not override_reason:
            raise HTTPException(
                status_code=400,
                detail="exchange_rate_override_reason is required when exchange_rate_overridden is true.",
            )

    return {
        "original_amount": original_amount,
        "original_currency": original_currency,
        "exchange_rate_to_base": effective_rate,
        "base_amount": base_amount,
        "base_currency": base_currency,
        "exchange_rate_source": rate_source,
        "exchange_rate_overridden": overridden,
        "exchange_rate_override_reason": override_reason,
    }


def _ensure_multi_currency_transaction_columns(db: Session) -> None:
    for statement in [
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS original_amount NUMERIC(12, 2)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS original_currency VARCHAR(10)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_to_base NUMERIC(18, 8)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS base_amount NUMERIC(14, 2)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS base_currency VARCHAR(10) DEFAULT 'ETB'",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_source VARCHAR(80)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_overridden BOOLEAN DEFAULT FALSE",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_override_reason TEXT",
    ]:
        db.execute(text(statement))


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


def _column_or_null(columns: set[str], column_name: str, sql_type: str = "text") -> str:
    if column_name in columns:
        return column_name
    return f"NULL::{sql_type}"


def _get_booking(db: Session, property_code: str, booking_id: int):
    columns = _table_columns(db, "bookings")
    row = db.execute(
        text(
            f"""
            SELECT
              id,
              hotel_id,
              property_code,
              guest_name,
              {_column_or_null(columns, "guest_email")} AS guest_email,
              {_column_or_null(columns, "guest_phone")} AS guest_phone,
              {_column_or_null(columns, "check_in_date", "date")} AS check_in_date,
              {_column_or_null(columns, "check_out_date", "date")} AS check_out_date,
              COALESCE({_column_or_null(columns, "currency")}, 'ETB') AS currency,
              booking_status,
              {_column_or_null(columns, "room_number")} AS room_number
            FROM bookings
            WHERE property_code = :p AND id = :bid
            LIMIT 1
            """
        ),
        {"p": property_code, "bid": booking_id},
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Booking {booking_id} not found for property {property_code}",
        )
    return row


def _ensure_checkout_receipts_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS checkout_receipts (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                booking_id INTEGER NOT NULL,
                folio_id INTEGER NOT NULL,
                receipt_number VARCHAR(80) UNIQUE NOT NULL,
                invoice_number VARCHAR(80) UNIQUE,
                guest_name VARCHAR(150),
                currency VARCHAR(10) DEFAULT 'ETB',
                total_charges NUMERIC(12, 2) DEFAULT 0,
                total_payments NUMERIC(12, 2) DEFAULT 0,
                balance NUMERIC(12, 2) DEFAULT 0,
                payment_method VARCHAR(80),
                payment_amount NUMERIC(12, 2) DEFAULT 0,
                status VARCHAR(50) DEFAULT 'issued',
                receipt_payload JSONB,
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


def _create_checkout_receipt(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    booking: Any,
    folio: Any,
    folio_id: int,
    payment_method: str,
    payment_amount: Decimal,
) -> dict[str, Any]:
    _ensure_checkout_receipts_table(db)
    booking_id = int(booking["id"])
    receipt_number = f"{property_code}-{business_date:%Y%m%d}-R{booking_id:06d}"
    invoice_number = f"{property_code}-{business_date:%Y%m%d}-I{booking_id:06d}"
    payload = {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "booking_id": booking_id,
        "folio_id": folio_id,
        "receipt_number": receipt_number,
        "invoice_number": invoice_number,
        "guest_name": booking.get("guest_name") or "Guest",
        "room_number": booking.get("room_number"),
        "check_in_date": booking.get("check_in_date").isoformat() if booking.get("check_in_date") else None,
        "check_out_date": booking.get("check_out_date").isoformat() if booking.get("check_out_date") else None,
        "currency": folio.get("currency") or booking.get("currency") or "ETB",
        "total_charges": str(_as_decimal(folio["total_charges"])),
        "total_payments": str(_as_decimal(folio["total_payments"])),
        "balance": str(_as_decimal(folio["balance"])),
        "payment_method": payment_method,
        "payment_amount": str(payment_amount),
    }
    row = db.execute(
        text(
            """
            INSERT INTO checkout_receipts (
                property_code,
                business_date,
                booking_id,
                folio_id,
                receipt_number,
                invoice_number,
                guest_name,
                currency,
                total_charges,
                total_payments,
                balance,
                payment_method,
                payment_amount,
                status,
                receipt_payload
            )
            VALUES (
                :property_code,
                :business_date,
                :booking_id,
                :folio_id,
                :receipt_number,
                :invoice_number,
                :guest_name,
                :currency,
                :total_charges,
                :total_payments,
                :balance,
                :payment_method,
                :payment_amount,
                'issued',
                CAST(:receipt_payload AS JSONB)
            )
            ON CONFLICT (receipt_number) DO UPDATE SET
                total_charges = EXCLUDED.total_charges,
                total_payments = EXCLUDED.total_payments,
                balance = EXCLUDED.balance,
                payment_method = EXCLUDED.payment_method,
                payment_amount = EXCLUDED.payment_amount,
                receipt_payload = EXCLUDED.receipt_payload
            RETURNING id
            """
        ),
        {
            **payload,
            "receipt_payload": json.dumps(payload, default=str),
        },
    ).mappings().first()
    return {**payload, "receipt_id": int(row["id"]) if row else None}


def _queue_checkout_receipt_notification(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    booking: Any,
    receipt: dict[str, Any],
) -> None:
    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=booking.get("guest_name") or "Guest",
        email=booking.get("guest_email"),
        phone=booking.get("guest_phone"),
    )
    link_guest_profile_to_booking(db, booking_id=int(booking["id"]), guest_profile=guest_profile)
    message = (
        f"Dear {booking.get('guest_name') or 'Guest'}, your checkout receipt "
        f"{receipt['receipt_number']} / invoice {receipt['invoice_number']} has been issued. "
        f"Total charges {receipt['currency']} {receipt['total_charges']}; "
        f"payments {receipt['currency']} {receipt['total_payments']}; "
        f"balance {receipt['currency']} {receipt['balance']}."
    )
    queue_guest_notification(
        db,
        property_code=property_code,
        booking_id=int(booking["id"]),
        guest_profile=guest_profile,
        guest_email=booking.get("guest_email"),
        guest_phone=booking.get("guest_phone"),
        action="checkout_receipt",
        message=message,
        business_date=business_date,
    )
    queue_guest_notification(
        db,
        property_code=property_code,
        booking_id=int(booking["id"]),
        guest_profile=guest_profile,
        guest_email=booking.get("guest_email"),
        guest_phone=booking.get("guest_phone"),
        action="guest_feedback_request",
        message=(
            f"Dear {booking.get('guest_name') or 'Guest'}, thank you for staying with us. "
            "Please share feedback about your experience so our team can follow up where needed."
        ),
        business_date=business_date,
    )


def _get_or_create_folio(db: Session, property_code: str, booking_id: int) -> int:
    row = db.execute(
        text(
            """
            SELECT id
            FROM folios
            WHERE property_code = :p AND booking_id = :bid
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"p": property_code, "bid": booking_id},
    ).first()

    if row:
        return int(row.id)

    booking = _get_booking(db, property_code, booking_id)

    created = db.execute(
        text(
            """
            INSERT INTO folios(
              property_code,
              booking_id,
              guest_name,
              currency,
              status
            )
            VALUES(
              :p,
              :bid,
              :guest_name,
              :currency,
              'open'
            )
            RETURNING id
            """
        ),
        {
            "p": property_code,
            "bid": booking_id,
            "guest_name": booking.get("guest_name") or "Guest",
            "currency": booking.get("currency") or "ETB",
        },
    ).first()

    if not created:
        raise HTTPException(
            status_code=500,
            detail=f"Could not create folio for booking {booking_id}",
        )

    return int(created.id)


def refresh_folio_totals(db: Session, folio_id: int) -> None:
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

    total_charges = _as_decimal(row["total_charges"] if row else 0)
    total_payments = _as_decimal(row["total_payments"] if row else 0)
    balance = total_charges - total_payments

    db.execute(
        text(
            """
            UPDATE folios
            SET
              total_charges = :charges,
              total_payments = :payments,
              balance = :balance
            WHERE id = :folio_id
            """
        ),
        {
            "folio_id": folio_id,
            "charges": total_charges,
            "payments": total_payments,
            "balance": balance,
        },
    )


def _read_folio_totals(db: Session, folio_id: int):
    row = db.execute(
        text(
            """
            SELECT
              id,
              booking_id,
              property_code,
              status,
              closed_at,
              currency,
              total_charges,
              total_payments,
              balance
            FROM folios
            WHERE id = :folio_id
            """
        ),
        {"folio_id": folio_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Folio {folio_id} not found")

    return row


@router.post("/process", dependencies=[Depends(verify_admin_token)])
def checkout_process(
    payload: CheckoutProcessIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = payload.property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_out",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    booking_id = int(payload.booking_id)
    pay_amount = _as_decimal(payload.pay_amount)

    try:
        booking = _get_booking(db, property_code, booking_id)
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        guest_profile = find_or_create_guest_profile(
            db,
            property_code=property_code,
            guest_name=booking.get("guest_name") or "Guest",
            email=booking.get("guest_email"),
            phone=booking.get("guest_phone"),
        )
        link_guest_profile_to_booking(db, booking_id=booking_id, guest_profile=guest_profile)
        link_guest_profile_to_folio(db, folio_id=folio_id, guest_profile=guest_profile)

        effective_currency = (
            payload.currency.strip().upper()
            if payload.currency and payload.currency.strip()
            else str(booking.get("currency") or "ETB").upper()
        )

        if pay_amount > 0:
            idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else f"checkout:{uuid4().hex}"
            _ensure_multi_currency_transaction_columns(db)
            exchange = _payment_exchange_payload(
                property_code=property_code,
                original_amount=pay_amount,
                original_currency=effective_currency,
                exchange_rate_to_base=payload.exchange_rate_to_base,
                exchange_rate_source=payload.exchange_rate_source,
                exchange_rate_overridden=payload.exchange_rate_overridden,
                exchange_rate_override_reason=payload.exchange_rate_override_reason,
            )
            ledger = post_finance_transaction(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                folio_id=folio_id,
                booking_id=booking_id,
                transaction_type="payment",
                amount=exchange["base_amount"],
                currency=exchange["base_currency"],
                direction="credit",
                payment_method=payload.pay_method,
                reference=payload.description,
                source_document_type="checkout_payment",
                source_document_id=booking_id,
                created_by=actor["email"],
                idempotency_key=idempotency_key,
                metadata={k: str(v) for k, v in exchange.items()},
                require_cashier_shift=True,
            )
            if ledger["replayed"]:
                raise HTTPException(status_code=409, detail="Checkout payment was already posted.")
            db.execute(
                text(
                    """
                    INSERT INTO folio_transactions(
                      folio_id,
                      property_code,
                      business_date,
                      txn_type,
                      category,
                      description,
                      amount,
                      currency,
                      booking_id,
                      original_amount,
                      original_currency,
                      exchange_rate_to_base,
                      base_amount,
                      base_currency,
                      exchange_rate_source,
                      exchange_rate_overridden,
                      exchange_rate_override_reason,
                      reference
                    )
                    VALUES(
                      :folio_id,
                      :property_code,
                      :business_date,
                      'payment',
                      :category,
                      :description,
                      :amount,
                      :currency,
                      :booking_id,
                      :original_amount,
                      :original_currency,
                      :exchange_rate_to_base,
                      :base_amount,
                      :base_currency,
                      :exchange_rate_source,
                      :exchange_rate_overridden,
                      :exchange_rate_override_reason,
                      :reference
                    )
                    """
                ),
                {
                    "folio_id": folio_id,
                    "property_code": property_code,
                    "business_date": payload.business_date,
                    "category": payload.pay_method,
                    "description": f"{payload.pay_method.replace('_', ' ').title()}: {payload.description}",
                    "amount": pay_amount,
                    "currency": effective_currency,
                    "booking_id": booking_id,
                    "reference": idempotency_key,
                    **exchange,
                },
            )

        refresh_folio_totals(db, folio_id)
        folio = _read_folio_totals(db, folio_id)

        balance = _as_decimal(folio["balance"])

        folio_closed = False
        booking_checked_out = False
        receipt: dict[str, Any] | None = None

        if payload.close_folio:
            if balance != Decimal("0"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot close folio with non-zero balance: {balance}",
                )

            db.execute(
                text(
                    """
                    UPDATE folios
                    SET
                      status = 'closed',
                      closed_at = now()
                    WHERE id = :folio_id
                    """
                ),
                {"folio_id": folio_id},
            )
            folio_closed = True

        if payload.mark_booking_checked_out:
            if balance != Decimal("0") and payload.close_folio:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot mark booking checked_out with non-zero balance: {balance}",
                )

            db.execute(
                text(
                    """
                    UPDATE bookings
                    SET
                      booking_status = 'checked_out',
                      checked_out_at = now(),
                      closed_balance = :closed_balance
                    WHERE id = :booking_id AND property_code = :property_code
                    """
                ),
                {
                    "booking_id": booking_id,
                    "property_code": property_code,
                    "closed_balance": balance,
                },
            )
            booking_checked_out = True
            room_number = str(booking.get("room_number") or "").strip()
            if room_number:
                _set_housekeeping_status(
                    db,
                    business_date=payload.business_date,
                    property_code=property_code,
                    room_number=room_number,
                    hk_status="vacant_dirty",
                    user_email=actor["email"],
                    action="room_marked_vacant_dirty_after_checkout",
                    note=f"Cashier checkout completed for booking {booking_id}.",
                )

        refresh_folio_totals(db, folio_id)
        folio = _read_folio_totals(db, folio_id)
        if folio_closed and booking_checked_out:
            receipt = _create_checkout_receipt(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                booking=booking,
                folio=folio,
                folio_id=folio_id,
                payment_method=payload.pay_method,
                payment_amount=pay_amount,
            )
            _queue_checkout_receipt_notification(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                booking=booking,
                receipt=receipt,
            )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="frontdesk",
            action="guest_checked_out",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "pay_amount": str(pay_amount),
                "pay_method": payload.pay_method,
                "folio_closed": folio_closed,
                "booking_checked_out": booking_checked_out,
                "balance": str(_as_decimal(folio["balance"])),
                "receipt_number": receipt.get("receipt_number") if receipt else None,
                "invoice_number": receipt.get("invoice_number") if receipt else None,
            },
        )

        db.commit()

        return {
            "ok": True,
            "property_code": property_code,
            "booking_id": booking_id,
            "folio_id": folio_id,
            "totals": {
                "total_charges": str(_as_decimal(folio["total_charges"])),
                "total_payments": str(_as_decimal(folio["total_payments"])),
                "balance": str(_as_decimal(folio["balance"])),
            },
            "folio_closed": folio_closed,
            "booking_checked_out": booking_checked_out,
            "receipt": receipt,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout failed: {e}")
