from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.audit_log_service import record_audit_log
from guzo_backend.services.business_date_lock_service import assert_business_date_editable
from guzo_backend.services.cashier_shift_service import approve_variance as approve_cashier_variance_service
from guzo_backend.services.cashier_shift_service import close_shift as close_cashier_shift_service
from guzo_backend.services.cashier_shift_service import current_shift as current_cashier_shift_service
from guzo_backend.services.cashier_shift_service import declare_totals as declare_cashier_totals_service
from guzo_backend.services.cashier_shift_service import open_shift as open_cashier_shift_service
from guzo_backend.services.city_ledger_service import transfer_folio as transfer_folio_to_ar
from guzo_backend.services.finance_transaction_service import (
    get_finance_transaction,
    post_finance_transaction,
    reverse_finance_transaction,
)
from guzo_backend.services.pms_security_service import (
    record_pms_audit_log,
    require_pms_permission,
    require_property_access,
)

router = APIRouter(prefix="/finance", tags=["Finance"])

PROPERTY_BASE_CURRENCIES = {
    "DRE001": "ETB",
}

ALLOWED_PAYMENT_METHODS = {
    "cash",
    "card",
    "telebirr",
    "cbebirr",
    "mobile_money",
    "pos",
    "bank_transfer",
}


class PostChargeIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    category: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)
    reference: str | None = None
    idempotency_key: str | None = None
    exchange_rate_to_base: Decimal | None = None
    exchange_rate_source: str | None = None
    exchange_rate_overridden: bool = False
    exchange_rate_override_reason: str | None = None

    @field_validator("property_code")
    @classmethod
    def validate_property_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_code is required")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("category is required")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description is required")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("currency is required")
        return v


class PostPaymentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    method: str = Field(..., min_length=1, validation_alias=AliasChoices("method", "payment_method"))
    description: str = Field("Payment", min_length=1, validation_alias=AliasChoices("description", "reference"))
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)
    exchange_rate_to_base: Decimal | None = None
    exchange_rate_source: str | None = None
    exchange_rate_overridden: bool = False
    exchange_rate_override_reason: str | None = None
    idempotency_key: str | None = None

    @field_validator("property_code")
    @classmethod
    def validate_property_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_code is required")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        m = v.strip().lower()
        if m not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"Unsupported payment method: {v}")
        return m

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description is required")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("currency is required")
        return v


class CashierCloseIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    cashier_name: str = Field("manager", min_length=1)
    declared_total: Decimal | None = None
    actual_cash: Decimal | None = None
    actual_card: Decimal | None = None
    actual_bank_transfer: Decimal | None = None
    actual_mobile_money: Decimal | None = None
    actual_unassigned: Decimal | None = None
    manager_approval_reason: str | None = None
    notes: str | None = None

    @field_validator("property_code")
    @classmethod
    def validate_property_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_code is required")
        return v

    @field_validator("cashier_name")
    @classmethod
    def validate_cashier_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cashier_name is required")
        return v


class CashierOpenIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    cashier_name: str = Field(..., min_length=1)
    opening_float: Decimal = Field(Decimal("0"), ge=0)
    notes: str | None = None

    @field_validator("property_code")
    @classmethod
    def validate_property_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_code is required")
        return v

    @field_validator("cashier_name")
    @classmethod
    def validate_cashier_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cashier_name is required")
        return v


class ApplyTaxServiceIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    taxable_amount: Decimal = Field(..., gt=0)
    tax_rate: Decimal = Field(Decimal("0.15"), ge=0)
    service_rate: Decimal = Field(Decimal("0.10"), ge=0)
    currency: str = Field("ETB", min_length=1)
    idempotency_key: str | None = None


class PostQuoteChargesIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    room_charge_amount: Decimal | None = None
    currency: str | None = None
    idempotency_key: str | None = None


class VoidTransactionIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    transaction_id: int
    business_date: date
    reason: str = Field(..., min_length=3)
    idempotency_key: str | None = None


class RefundIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    amount: Decimal = Field(..., gt=0)
    method: str = Field(..., min_length=1, validation_alias=AliasChoices("method", "payment_method"))
    reason: str = Field(..., min_length=3)
    currency: str = Field("ETB", min_length=1)
    idempotency_key: str | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        m = v.strip().lower()
        if m not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"Unsupported refund method: {v}")
        return m


class TransferBalanceIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    billing_account: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=3)
    idempotency_key: str | None = None


class CorrectionIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    transaction_id: int
    business_date: date
    corrected_amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)
    reference: str | None = None


class AdjustmentIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)
    direction: str = Field(..., pattern="^(debit|credit)$")
    reason: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)
    folio_id: int | None = None
    booking_id: int | None = None
    account_reference: str | None = None


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
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS payment_method VARCHAR(80)",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS reference VARCHAR(160)",
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


def _currency_from_notes(notes: str | None) -> str | None:
    match = re.search(r"Currency:\s*([A-Za-z]{3})", str(notes or ""), re.IGNORECASE)
    return match.group(1).upper() if match else None


def _get_booking(db: Session, property_code: str, booking_id: int):
    booking_columns = _table_columns(db, "bookings")
    currency_expr = "COALESCE(currency, 'ETB')" if "currency" in booking_columns else "'ETB'"
    notes_expr = "notes" if "notes" in booking_columns else "NULL"
    row = db.execute(
        text(
            f"""
            SELECT
              id,
              property_code,
              guest_name,
              {currency_expr} AS currency,
              {notes_expr} AS notes,
              check_in_date,
              check_out_date,
              booking_status
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
    booking = dict(row)
    note_currency = _currency_from_notes(booking.get("notes"))
    if note_currency:
        booking["currency"] = note_currency
    else:
        booking["currency"] = str(booking.get("currency") or "ETB").upper()
    return booking


def _normalize_property_code(property_code: str) -> str:
    return property_code.strip().upper()


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


def _booking_amount_sql(columns: set[str]) -> str:
    if "total_amount" in columns:
        return "COALESCE(b.total_amount, 0)"
    if "total_revenue_etb" in columns:
        return "COALESCE(b.total_revenue_etb, 0)"
    if "total_amount_etb" in columns:
        return "COALESCE(b.total_amount_etb, 0)"
    return "0"


def _booking_column_sql(columns: set[str], column_name: str, fallback: str) -> str:
    if column_name in columns:
        return f"b.{column_name}"
    return fallback


def _money(value: Any) -> float:
    return float(_as_decimal(value))


def _active_tax_service_rule(db: Session, property_code: str) -> dict[str, Any]:
    if not _table_exists(db, "tax_service_rules"):
        return {
            "rule_name": None,
            "tax_percent": None,
            "service_charge_percent": None,
            "source": "not_configured",
        }

    row = db.execute(
        text(
            """
            SELECT rule_name, tax_percent, service_charge_percent
            FROM tax_service_rules
            WHERE property_code = :property_code
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code},
    ).mappings().first()
    if not row:
        return {
            "rule_name": None,
            "tax_percent": None,
            "service_charge_percent": None,
            "source": "not_configured",
        }
    return {
        "rule_name": row["rule_name"],
        "tax_percent": float(row["tax_percent"] or 0),
        "service_charge_percent": float(row["service_charge_percent"] or 0),
        "source": "tax_service_rules",
    }


def _booking_quote_for_folio(db: Session, property_code: str, booking_id: int) -> dict[str, Any]:
    columns = _table_columns(db, "bookings")
    amount_expr = _booking_amount_sql(columns)
    rate_expr = _booking_column_sql(columns, "rate_per_night_etb", "NULL")
    currency_expr = _booking_column_sql(columns, "currency", "'ETB'")
    row = db.execute(
        text(
            f"""
            SELECT
              id,
              check_in_date,
              check_out_date,
              {amount_expr} AS total_amount,
              {rate_expr} AS rate_per_night,
              COALESCE({currency_expr}, 'ETB') AS currency
            FROM bookings b
            WHERE property_code = :property_code
              AND id = :booking_id
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property.")

    nights = 1
    if row["check_in_date"] and row["check_out_date"]:
        nights = max((row["check_out_date"] - row["check_in_date"]).days, 1)
    rate = _as_decimal(row["rate_per_night"]) if row["rate_per_night"] is not None else Decimal("0")
    total = _as_decimal(row["total_amount"])
    room_charge = rate * Decimal(nights) if rate > 0 else total
    if room_charge <= 0:
        raise HTTPException(status_code=400, detail="Reservation quote value is missing; cannot post room charge from quote.")
    return {
        "nights": nights,
        "rate_per_night": rate,
        "room_charge": room_charge.quantize(Decimal("0.01")),
        "total_amount": total,
        "currency": str(row["currency"] or "ETB").upper(),
    }


def _estimate_reservation_value(room_type: Any, check_in: Any, check_out: Any) -> float:
    if not check_in or not check_out:
        return 0.0

    nights = max((check_out - check_in).days, 1)
    room_label = str(room_type or "").lower()
    if "suite" in room_label:
        nightly_rate = 6500
    elif "family" in room_label:
        nightly_rate = 5000
    elif "deluxe" in room_label:
        nightly_rate = 3500
    else:
        nightly_rate = 2500
    return float(nights * nightly_rate)


def _get_or_create_folio(db: Session, property_code: str, booking_id: int) -> int:
    booking = _get_booking(db, property_code, booking_id)
    row = db.execute(
        text(
            """
            SELECT id, COALESCE(currency, 'ETB') AS currency
            FROM folios
            WHERE property_code = :p AND booking_id = :bid
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"p": property_code, "bid": booking_id},
    ).first()

    if row:
        booking_currency = str(booking.get("currency") or "ETB").upper()
        folio_currency = str(row.currency or "ETB").upper()
        if booking_currency != folio_currency:
            db.execute(
                text(
                    """
                    UPDATE folios
                    SET currency = :currency
                    WHERE id = :folio_id
                    """
                ),
                {"currency": booking_currency, "folio_id": int(row.id)},
            )
        return int(row.id)

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
              COALESCE(SUM(CASE
                WHEN txn_type = 'payment' THEN amount
                WHEN txn_type = 'refund' THEN -amount
                ELSE 0
              END), 0) AS total_payments
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


def _ensure_cashier_sessions_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS cashier_sessions (
              id SERIAL PRIMARY KEY,
              property_code TEXT NOT NULL,
              business_date DATE NOT NULL,
              cashier_name TEXT NOT NULL,
              cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
              card NUMERIC(12, 2) NOT NULL DEFAULT 0,
              bank_transfer NUMERIC(12, 2) NOT NULL DEFAULT 0,
              mobile_money NUMERIC(12, 2) NOT NULL DEFAULT 0,
              unassigned NUMERIC(12, 2) NOT NULL DEFAULT 0,
              opening_float NUMERIC(12, 2) NOT NULL DEFAULT 0,
              actual_cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
              actual_card NUMERIC(12, 2) NOT NULL DEFAULT 0,
              actual_bank_transfer NUMERIC(12, 2) NOT NULL DEFAULT 0,
              actual_mobile_money NUMERIC(12, 2) NOT NULL DEFAULT 0,
              actual_unassigned NUMERIC(12, 2) NOT NULL DEFAULT 0,
              expected_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
              declared_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
              variance NUMERIC(12, 2) NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'closed',
              notes TEXT,
              opened_at TIMESTAMPTZ,
              closed_by TEXT,
              manager_approved_by TEXT,
              manager_approval_reason TEXT,
              closed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    for statement in [
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS unassigned NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS opening_float NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS actual_cash NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS actual_card NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS actual_bank_transfer NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS actual_mobile_money NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS actual_unassigned NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS opened_at TIMESTAMPTZ",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS closed_by TEXT",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS manager_approved_by TEXT",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS manager_approval_reason TEXT",
    ]:
        db.execute(text(statement))


def _ensure_folio_accounting_columns(db: Session) -> None:
    for statement in [
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS voided_by TEXT",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS void_reason TEXT",
        "ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS original_transaction_id INTEGER",
        "ALTER TABLE folios ADD COLUMN IF NOT EXISTS transferred_to TEXT",
        "ALTER TABLE folios ADD COLUMN IF NOT EXISTS transfer_reason TEXT",
        "ALTER TABLE folios ADD COLUMN IF NOT EXISTS transferred_at TIMESTAMPTZ",
    ]:
        db.execute(text(statement))


@router.get("/control-report")
def get_finance_control_report(
    property_code: str,
    business_date: date,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    has_folios = _table_exists(db, "folios")
    has_folio_transactions = _table_exists(db, "folio_transactions")
    booking_columns = _table_columns(db, "bookings")
    booking_amount_expr = _booking_amount_sql(booking_columns)
    payment_status_expr = _booking_column_sql(booking_columns, "payment_status", "'pending'")
    booking_status_expr = _booking_column_sql(booking_columns, "booking_status", "'pending'")
    source_expr = _booking_column_sql(booking_columns, "source", "'direct'")
    room_type_expr = _booking_column_sql(booking_columns, "room_type", "NULL")
    payment_method_expr = _booking_column_sql(booking_columns, "payment_method", "NULL")

    booking_row = db.execute(
        text(
            f"""
            SELECT
              COALESCE(SUM({booking_amount_expr}), 0) AS gross_booking_revenue,
              COALESCE(SUM(CASE WHEN LOWER(COALESCE({payment_status_expr}, 'pending')) IN ('pending', 'unpaid') THEN {booking_amount_expr} ELSE 0 END), 0) AS pending_payment_total,
              COALESCE(SUM(CASE WHEN LOWER(COALESCE({payment_status_expr}, '')) IN ('deposit_paid', 'paid', 'guaranteed') THEN {booking_amount_expr} ELSE 0 END), 0) AS guaranteed_value,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({booking_status_expr}, '')) = 'pending_guarantee') AS pending_guarantee_count,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({booking_status_expr}, '')) IN ('in_house', 'checked_in')) AS in_house_count,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({booking_status_expr}, '')) NOT IN ('cancelled', 'checked_out', 'no_show', 'no-show')) AS active_reservations
            FROM bookings b
            WHERE b.property_code = :property_code
              AND b.check_in_date <= :business_date
              AND b.check_out_date >= :business_date
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()

    txn_summary = {
        "room_revenue": 0,
        "fnb_revenue": 0,
        "other_revenue": 0,
        "payments_collected": 0,
        "refunds": 0,
        "taxable_revenue": 0,
    }
    payment_ledger: list[dict[str, Any]] = []
    folio_transaction_audit: list[dict[str, Any]] = []
    guest_ledger: list[dict[str, Any]] = []
    duplicate_open_folios: list[dict[str, Any]] = []

    if has_folio_transactions:
        _ensure_multi_currency_transaction_columns(db)
        txn_row = db.execute(
            text(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN txn_type = 'charge' AND category IN ('room', 'room_revenue') THEN amount ELSE 0 END), 0) AS room_revenue,
                  COALESCE(SUM(CASE WHEN txn_type = 'charge' AND category IN ('fnb', 'food', 'restaurant', 'banquet') THEN amount ELSE 0 END), 0) AS fnb_revenue,
                  COALESCE(SUM(CASE WHEN txn_type = 'charge' AND category NOT IN ('room', 'room_revenue', 'fnb', 'food', 'restaurant', 'banquet', 'tax', 'vat', 'service_charge') THEN amount ELSE 0 END), 0) AS other_revenue,
                  COALESCE(SUM(CASE WHEN txn_type = 'payment' THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS payments_collected,
                  COALESCE(SUM(CASE WHEN txn_type = 'refund' THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS refunds,
                  COALESCE(SUM(CASE WHEN txn_type = 'charge' THEN amount ELSE 0 END), 0) AS taxable_revenue
                FROM folio_transactions
                WHERE property_code = :property_code
                  AND business_date = :business_date
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().first()
        txn_summary = {key: _money((txn_row or {}).get(key)) for key in txn_summary}

        payment_rows = db.execute(
            text(
                """
                SELECT
                  ft.id,
                  ft.booking_id,
                  COALESCE(b.guest_name, f.guest_name, 'Guest') AS guest_name,
                  ft.business_date,
                  ft.category AS payment_method,
                  ft.description,
                  ft.amount,
                  ft.currency,
                  ft.original_amount,
                  ft.original_currency,
                  ft.exchange_rate_to_base,
                  ft.base_amount,
                  ft.base_currency,
                  ft.exchange_rate_source,
                  ft.exchange_rate_overridden,
                  ft.exchange_rate_override_reason
                FROM folio_transactions ft
                LEFT JOIN folios f ON f.id = ft.folio_id
                LEFT JOIN bookings b ON b.id = ft.booking_id AND b.property_code = ft.property_code
                WHERE ft.property_code = :property_code
                  AND ft.business_date = :business_date
                  AND ft.txn_type = 'payment'
                ORDER BY ft.id DESC
                LIMIT 50
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().all()
        payment_ledger = [
            {
                "id": row["id"],
                "booking_id": row["booking_id"],
                "guest_name": row["guest_name"],
                "payment_method": row["payment_method"],
                "description": row["description"],
                "amount": _money(row["amount"]),
                "currency": row["currency"],
                "original_amount": _money(row["original_amount"] or row["amount"]),
                "original_currency": row["original_currency"] or row["currency"],
                "exchange_rate_to_base": _money(row["exchange_rate_to_base"]) if row["exchange_rate_to_base"] is not None else None,
                "base_amount": _money(row["base_amount"]) if row["base_amount"] is not None else None,
                "base_currency": row["base_currency"] or _base_currency_for_property(property_code),
                "exchange_rate_source": row["exchange_rate_source"],
                "exchange_rate_overridden": bool(row["exchange_rate_overridden"]),
                "exchange_rate_override_reason": row["exchange_rate_override_reason"],
            }
            for row in payment_rows
        ]

        if not txn_summary["payments_collected"] and payment_ledger:
            txn_summary["payments_collected"] = sum(row["base_amount"] or 0 for row in payment_ledger)

        audit_rows = db.execute(
            text(
                """
                SELECT
                  ft.id,
                  ft.booking_id,
                  COALESCE(b.guest_name, f.guest_name, 'Guest') AS guest_name,
                  ft.business_date,
                  ft.txn_type,
                  ft.category,
                  ft.description,
                  ft.amount,
                  ft.currency,
                  ft.original_amount,
                  ft.original_currency,
                  ft.exchange_rate_to_base,
                  ft.base_amount,
                  ft.base_currency
                FROM folio_transactions ft
                LEFT JOIN folios f ON f.id = ft.folio_id
                LEFT JOIN bookings b ON b.id = ft.booking_id AND b.property_code = ft.property_code
                WHERE ft.property_code = :property_code
                  AND ft.business_date = :business_date
                ORDER BY ft.id DESC
                LIMIT 75
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().all()
        folio_transaction_audit = [
            {
                "id": row["id"],
                "booking_id": row["booking_id"],
                "guest_name": row["guest_name"],
                "txn_type": row["txn_type"],
                "category": row["category"],
                "description": row["description"],
                "amount": _money(row["amount"]),
                "currency": row["currency"],
                "original_amount": _money(row["original_amount"] or row["amount"]),
                "original_currency": row["original_currency"] or row["currency"],
                "exchange_rate_to_base": _money(row["exchange_rate_to_base"]) if row["exchange_rate_to_base"] is not None else None,
                "base_amount": _money(row["base_amount"]) if row["base_amount"] is not None else None,
                "base_currency": row["base_currency"] or _base_currency_for_property(property_code),
            }
            for row in audit_rows
        ]

    if has_folios:
        ledger_rows = db.execute(
            text(
                """
                SELECT
                  f.id AS folio_id,
                  f.booking_id,
                  f.guest_name,
                  b.room_number,
                  COALESCE(f.total_charges, 0) AS charges,
                  COALESCE(f.total_payments, 0) AS payments,
                  COALESCE(f.balance, 0) AS balance,
                  COALESCE(f.currency, 'ETB') AS currency,
                  b.booking_status,
                  COALESCE(b.payment_status, 'pending') AS payment_status
                FROM folios f
                LEFT JOIN bookings b ON b.id = f.booking_id AND b.property_code = f.property_code
                WHERE f.property_code = :property_code
                  AND COALESCE(f.status, 'open') = 'open'
                ORDER BY ABS(COALESCE(f.balance, 0)) DESC, f.id DESC
                LIMIT 75
                """
            ),
            {"property_code": property_code},
        ).mappings().all()
        guest_ledger = [
            {
                "folio_id": row["folio_id"],
                "booking_id": row["booking_id"],
                "guest_name": row["guest_name"],
                "room_number": row["room_number"],
                "charges": _money(row["charges"]),
                "payments": _money(row["payments"]),
                "balance": _money(row["balance"]),
                "currency": row["currency"],
                "booking_status": row["booking_status"],
                "payment_status": row["payment_status"],
            }
            for row in ledger_rows
        ]

        if not payment_ledger:
            fallback_payment_rows = db.execute(
                text(
                    """
                    SELECT
                      f.id AS folio_id,
                      f.booking_id,
                      f.guest_name,
                      COALESCE(f.total_payments, 0) AS amount,
                      COALESCE(f.currency, 'ETB') AS currency
                    FROM folios f
                    WHERE f.property_code = :property_code
                      AND COALESCE(f.status, 'open') = 'open'
                      AND COALESCE(f.total_payments, 0) > 0
                    ORDER BY f.id DESC
                    LIMIT 50
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
            payment_ledger = [
                {
                    "id": f"folio-{row['folio_id']}",
                    "booking_id": row["booking_id"],
                    "guest_name": row["guest_name"],
                    "payment_method": "folio_total",
                    "description": "Payment total from open folio; transaction-level payment record not found for this business date.",
                    "amount": _money(row["amount"]),
                    "currency": row["currency"],
                    "original_amount": _money(row["amount"]),
                    "original_currency": row["currency"],
                    "exchange_rate_to_base": 1.0 if row["currency"] == _base_currency_for_property(property_code) else None,
                    "base_amount": _money(row["amount"]) if row["currency"] == _base_currency_for_property(property_code) else None,
                    "base_currency": _base_currency_for_property(property_code),
                    "exchange_rate_source": "folio_total_fallback",
                    "exchange_rate_overridden": False,
                    "exchange_rate_override_reason": None,
                }
                for row in fallback_payment_rows
            ]
            txn_summary["payments_collected"] = sum(row["base_amount"] or 0 for row in payment_ledger)

        duplicate_rows = db.execute(
            text(
                """
                SELECT
                  booking_id,
                  COUNT(*) AS open_folio_count,
                  STRING_AGG(id::TEXT, ', ' ORDER BY id) AS folio_ids
                FROM folios
                WHERE property_code = :property_code
                  AND COALESCE(status, 'open') = 'open'
                  AND booking_id IS NOT NULL
                GROUP BY booking_id
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, booking_id DESC
                LIMIT 25
                """
            ),
            {"property_code": property_code},
        ).mappings().all()
        duplicate_open_folios = [
            {
                "booking_id": row["booking_id"],
                "open_folio_count": int(row["open_folio_count"] or 0),
                "folio_ids": row["folio_ids"],
            }
            for row in duplicate_rows
        ]

    folio_id_expr = "f.id" if has_folios else "NULL::integer"
    folio_status_expr = "CASE WHEN f.id IS NULL THEN 'folio_pending' ELSE 'folio_prepared' END" if has_folios else "'folio_pending'"
    folio_join_sql = """
            LEFT JOIN folios f
              ON f.property_code = b.property_code
             AND f.booking_id = b.id
             AND COALESCE(f.status, 'open') = 'open'
    """ if has_folios else ""

    deposit_rows = db.execute(
        text(
            f"""
            SELECT
                      b.id AS booking_id,
              b.guest_name,
              b.check_in_date,
              b.check_out_date,
              {room_type_expr} AS room_type,
              {payment_method_expr} AS payment_method,
              COALESCE({payment_status_expr}, 'pending') AS payment_status,
              {booking_status_expr} AS booking_status,
              {booking_amount_expr} AS reservation_value,
              {source_expr} AS source,
              {folio_id_expr} AS folio_id,
              {folio_status_expr} AS folio_status
            FROM bookings b
            {folio_join_sql}
            WHERE b.property_code = :property_code
              AND LOWER(COALESCE({booking_status_expr}, '')) IN ('pending_guarantee', 'confirmed')
              AND LOWER(COALESCE({payment_status_expr}, 'pending')) IN ('pending', 'unpaid', 'deposit_paid', 'guaranteed')
              AND b.check_in_date >= :business_date
            ORDER BY b.check_in_date, b.id
            LIMIT 75
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().all()
    deposit_ledger = [
        {
            "booking_id": row["booking_id"],
            "guest_name": row["guest_name"],
            "arrival": row["check_in_date"].isoformat() if row["check_in_date"] else None,
            "departure": row["check_out_date"].isoformat() if row["check_out_date"] else None,
            "room_type": row["room_type"],
            "payment_method": row["payment_method"],
            "payment_status": row["payment_status"],
            "booking_status": row["booking_status"],
            "reservation_value": (
                _money(row["reservation_value"])
                or _estimate_reservation_value(
                    row["room_type"],
                    row["check_in_date"],
                    row["check_out_date"],
                )
            ),
            "stored_reservation_value": _money(row["reservation_value"]),
            "value_source": "stored_amount" if _money(row["reservation_value"]) else "estimated_room_rate",
            "source": row["source"],
            "folio_id": row["folio_id"],
            "folio_status": row["folio_status"],
            "deposit_action": (
                "Deposit Expected"
                if str(row["payment_status"]).lower() in {"pending", "unpaid"}
                else "Deposit/Folio Ready"
            ),
        }
        for row in deposit_rows
    ]

    if _table_exists(db, "public_booking_requests"):
        public_deposit_rows = db.execute(
            text(
                """
                SELECT
                  id AS request_id,
                  guest_name,
                  check_in_date,
                  check_out_date,
                  room_type,
                  booking_status,
                  deposit_status,
                  COALESCE(channel, source, 'public_request') AS source
                FROM public_booking_requests
                WHERE property_code = :property_code
                  AND check_in_date >= :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('pending_request', 'reviewed', 'tentative', 'deposit_requested', 'deposit_required')
                  AND LOWER(COALESCE(deposit_status, 'pending')) NOT IN ('paid', 'deposit_paid')
                ORDER BY check_in_date, id
                LIMIT 50
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().all()
        deposit_ledger.extend(
            {
                "booking_id": f"request-{row['request_id']}",
                "request_id": row["request_id"],
                "guest_name": row["guest_name"],
                "arrival": row["check_in_date"].isoformat() if row["check_in_date"] else None,
                "departure": row["check_out_date"].isoformat() if row["check_out_date"] else None,
                "room_type": row["room_type"],
                "payment_method": None,
                "payment_status": row["deposit_status"] or "pending",
                "booking_status": row["booking_status"],
                "reservation_value": _estimate_reservation_value(
                    row["room_type"],
                    row["check_in_date"],
                    row["check_out_date"],
                ),
                "stored_reservation_value": 0,
                "value_source": "estimated_room_rate",
                "source": row["source"],
                "folio_id": None,
                "folio_status": "pending_request_not_converted",
                "deposit_action": "Deposit Expected",
            }
            for row in public_deposit_rows
        )

    room_revenue = txn_summary["room_revenue"] or _money((booking_row or {}).get("gross_booking_revenue"))
    fnb_revenue = txn_summary["fnb_revenue"]
    other_revenue = txn_summary["other_revenue"]
    gross_revenue = room_revenue + fnb_revenue + other_revenue
    service_charge = round(gross_revenue * 0.10, 2)
    tax_collected = round(gross_revenue * 0.15, 2)
    net_revenue = round(gross_revenue - tax_collected, 2)
    guest_ledger_balance = sum(row["balance"] for row in guest_ledger)
    deposit_ledger_balance = sum(
        row["reservation_value"]
        for row in deposit_ledger
        if str(row["payment_status"]).lower() == "deposit_paid"
    )
    ar_balance = _money((booking_row or {}).get("pending_payment_total"))

    trial_balance = {
        "guest_ledger_balance": round(guest_ledger_balance, 2),
        "deposit_ledger_balance": round(deposit_ledger_balance, 2),
        "ar_city_ledger_balance": round(ar_balance, 2),
        "revenue_ledger": round(gross_revenue, 2),
        "payment_ledger": round(txn_summary["payments_collected"], 2),
        "tax_ledger": tax_collected,
        "closing_balance": round(guest_ledger_balance + deposit_ledger_balance + ar_balance, 2),
    }
    finance_exceptions = [
        {
            "key": "missing_folio_tables",
            "severity": "warning",
            "message": "Folio tables are not configured yet. Guest ledger is returned as zero.",
        }
        for configured in [has_folios and has_folio_transactions]
        if not configured
    ]
    if int((booking_row or {}).get("pending_guarantee_count") or 0):
        finance_exceptions.append(
            {
                "key": "pending_guarantees",
                "severity": "warning",
                "message": "Pending guarantee reservations require deposit, card guarantee, or approved pay-at-hotel review.",
            }
        )
    if guest_ledger_balance < 0:
        finance_exceptions.append(
            {
                "key": "guest_credit_balances",
                "severity": "warning",
                "message": "Guest ledger has credit balances. Review deposits posted as folio payments, duplicate folios, or missing room charges.",
            }
        )
    if duplicate_open_folios:
        finance_exceptions.append(
            {
                "key": "duplicate_open_folios",
                "severity": "critical",
                "message": "Duplicate open folios detected. One primary folio per booking should be used unless a split folio was intentionally created.",
                "count": len(duplicate_open_folios),
                "rows": duplicate_open_folios,
            }
        )
    zero_value_deposits = [
        row
        for row in deposit_ledger
        if not row["stored_reservation_value"] and row["reservation_value"]
    ]
    if zero_value_deposits:
        finance_exceptions.append(
            {
                "key": "estimated_reservation_values",
                "severity": "warning",
                "message": "Some reservation records have stored amount 0; deposit ledger is using estimated room-rate value until booking totals are corrected.",
                "count": len(zero_value_deposits),
            }
        )
    if payment_ledger and all(str(row["payment_method"]).lower() == "folio_total" for row in payment_ledger):
        finance_exceptions.append(
            {
                "key": "payment_ledger_fallback",
                "severity": "warning",
                "message": "Payment ledger is using folio total fallback because same-day transaction-level payment records were not found.",
            }
        )

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "finance_dashboard": {
            "gross_booking_value": round(_money((booking_row or {}).get("gross_booking_revenue")), 2),
            "today_revenue": round(gross_revenue, 2),
            "payments_collected": round(txn_summary["payments_collected"], 2),
            "pending_payments": round(ar_balance, 2),
            "guest_ledger_balance": trial_balance["guest_ledger_balance"],
            "deposit_ledger_balance": trial_balance["deposit_ledger_balance"],
            "ar_balance": trial_balance["ar_city_ledger_balance"],
            "tax_collected": tax_collected,
            "refunds": round(txn_summary["refunds"], 2),
            "open_folios": len(guest_ledger),
            "pending_guarantee_reservations": int((booking_row or {}).get("pending_guarantee_count") or 0),
            "deposit_expected": sum(
                1
                for row in deposit_ledger
                if str(row.get("deposit_action", "")).lower() == "deposit expected"
            ),
            "folios_prepared": sum(
                1
                for row in deposit_ledger
                if str(row.get("folio_status", "")).lower() == "folio_prepared"
            ),
        },
        "daily_revenue": {
            "room_revenue": round(room_revenue, 2),
            "food_beverage_revenue": round(fnb_revenue, 2),
            "other_income": round(other_revenue, 2),
            "taxes": tax_collected,
            "service_charge": service_charge,
            "discounts": 0,
            "adjustments": 0,
            "payments_collected": round(txn_summary["payments_collected"], 2),
            "refunds": round(txn_summary["refunds"], 2),
            "gross_revenue": round(gross_revenue, 2),
            "net_revenue": net_revenue,
        },
        "trial_balance": trial_balance,
        "guest_ledger": guest_ledger,
        "deposit_ledger": deposit_ledger,
        "payment_ledger": payment_ledger,
        "tax_report": {
            "vat_estimate": tax_collected,
            "service_charge": service_charge,
            "taxable_revenue": round(gross_revenue, 2),
            "tax_exempt_revenue": 0,
        },
        "folio_transaction_audit": folio_transaction_audit,
        "cashier_shift": {
            "cash": round(
                sum((row.get("base_amount") or 0) for row in payment_ledger if str(row["payment_method"]).lower() == "cash"),
                2,
            ),
            "card": round(
                sum((row.get("base_amount") or 0) for row in payment_ledger if str(row["payment_method"]).lower() in {"card", "pos"}),
                2,
            ),
            "bank_transfer": round(
                sum((row.get("base_amount") or 0) for row in payment_ledger if str(row["payment_method"]).lower() == "bank_transfer"),
                2,
            ),
            "mobile_money": round(
                sum((row.get("base_amount") or 0) for row in payment_ledger if str(row["payment_method"]).lower() in {"telebirr", "cbebirr", "mobile_money"}),
                2,
            ),
            "unassigned": round(
                sum((row.get("base_amount") or 0) for row in payment_ledger if str(row["payment_method"]).lower() == "folio_total"),
                2,
            ),
            "variance": 0,
        },
        "duplicate_open_folios": duplicate_open_folios,
        "ar_city_ledger": {
            "status": "not_configured",
            "balance": round(ar_balance, 2),
            "message": "Structured AR invoices are not configured yet; using pending booking value as interim AR exposure.",
            "rows": [],
        },
        "accounting_lock": {
            "status": "open",
            "business_date": business_date.isoformat(),
            "locked_by": None,
            "locked_at": None,
        },
        "finance_exceptions": finance_exceptions,
    }


@router.post("/cashier/close")
def close_cashier_session(
    payload: CashierCloseIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.close_cashier",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="close_cashier",
    )
    active = current_cashier_shift_service(db, property_code=property_code, business_date=payload.business_date, user_email=actor["email"])
    if not active:
        raise HTTPException(status_code=409, detail="No active cashier shift is assigned to the current user.")
    try:
        declared = {
            "cash": payload.actual_cash if payload.actual_cash is not None else active["expected_by_method"]["cash"],
            "card": payload.actual_card if payload.actual_card is not None else active["expected_by_method"]["card"],
            "bank_transfer": payload.actual_bank_transfer if payload.actual_bank_transfer is not None else active["expected_by_method"]["bank_transfer"],
            "mobile_money": payload.actual_mobile_money if payload.actual_mobile_money is not None else active["expected_by_method"]["mobile_money"],
            "unassigned": payload.actual_unassigned if payload.actual_unassigned is not None else active["expected_by_method"]["unassigned"],
        }
        declared_shift = declare_cashier_totals_service(db, property_code=property_code, shift_id=int(active["id"]), declared=declared, actor=actor["email"])
        if abs(_as_decimal(declared_shift["variance"])) >= Decimal("0.01"):
            reason = (payload.manager_approval_reason or "").strip()
            if not reason:
                raise HTTPException(status_code=409, detail="Manager approval is required for cashier variance.")
            approver = require_pms_permission(db, permission_key="finance.approve_variance", property_code=property_code, user_email=x_pms_user_email)
            approve_cashier_variance_service(db, property_code=property_code, shift_id=int(active["id"]), reason=reason, actor=approver["email"])
        result = close_cashier_shift_service(db, property_code=property_code, shift_id=int(active["id"]), actor=actor["email"], notes=payload.notes)
        db.commit()
        return {"ok": True, "session_id": int(result["id"]), "property_code": property_code, "business_date": payload.business_date.isoformat(), "cashier_name": result["cashier_name"], "expected_total": float(result["expected_total"]), "declared_total": float(result["declared_total"]), "variance": float(result["variance"]), "status": result["status"]}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Close cashier session failed: {exc}")

    has_folio_transactions = _table_exists(db, "folio_transactions")

    try:
        totals = {
            "cash": Decimal("0"),
            "card": Decimal("0"),
            "bank_transfer": Decimal("0"),
            "mobile_money": Decimal("0"),
            "unassigned": Decimal("0"),
        }

        if has_folio_transactions:
            _ensure_multi_currency_transaction_columns(db)
            row = db.execute(
                text(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN LOWER(category) = 'cash' THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS cash,
                      COALESCE(SUM(CASE WHEN LOWER(category) IN ('card', 'pos') THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS card,
                      COALESCE(SUM(CASE WHEN LOWER(category) = 'bank_transfer' THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS bank_transfer,
                      COALESCE(SUM(CASE WHEN LOWER(category) IN ('telebirr', 'cbebirr', 'mobile_money') THEN COALESCE(base_amount, CASE WHEN COALESCE(currency, 'ETB') = 'ETB' THEN amount ELSE 0 END) ELSE 0 END), 0) AS mobile_money
                    FROM folio_transactions
                    WHERE property_code = :property_code
                      AND business_date = :business_date
                      AND txn_type = 'payment'
                    """
                ),
                {
                    "property_code": property_code,
                    "business_date": payload.business_date,
                },
            ).mappings().first()
            if row:
                totals.update({key: _as_decimal(row.get(key)) for key in row.keys() if key in totals})

        if not sum(totals.values(), Decimal("0")) and _table_exists(db, "folios"):
            fallback_total = db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(COALESCE(total_payments, 0)), 0) AS total_payments
                    FROM folios
                    WHERE property_code = :property_code
                      AND COALESCE(status, 'open') = 'open'
                      AND COALESCE(total_payments, 0) > 0
                    """
                ),
                {"property_code": property_code},
            ).scalar()
            totals["unassigned"] = _as_decimal(fallback_total)

        expected_total = sum(totals.values(), Decimal("0"))
        actual_totals = {
            "cash": payload.actual_cash if payload.actual_cash is not None else totals["cash"],
            "card": payload.actual_card if payload.actual_card is not None else totals["card"],
            "bank_transfer": (
                payload.actual_bank_transfer
                if payload.actual_bank_transfer is not None
                else totals["bank_transfer"]
            ),
            "mobile_money": (
                payload.actual_mobile_money
                if payload.actual_mobile_money is not None
                else totals["mobile_money"]
            ),
            "unassigned": (
                payload.actual_unassigned
                if payload.actual_unassigned is not None
                else totals["unassigned"]
            ),
        }
        declared_total = (
            payload.declared_total
            if payload.declared_total is not None
            else sum(actual_totals.values(), Decimal("0"))
        )
        variance = declared_total - expected_total
        manager_approved_by = None
        manager_approval_reason = (payload.manager_approval_reason or "").strip()
        if abs(variance) >= Decimal("0.01"):
            approver = require_pms_permission(
                db,
                permission_key="finance.approve_variance",
                property_code=property_code,
                user_email=x_pms_user_email,
            )
            manager_approved_by = approver["email"]
            if not manager_approval_reason:
                raise HTTPException(
                    status_code=409,
                    detail="Manager approval reason is required for cashier variance.",
                )

        _ensure_cashier_sessions_table(db)
        created = db.execute(
            text(
                """
                INSERT INTO cashier_sessions(
                  property_code,
                  business_date,
                  cashier_name,
                  cash,
                  card,
                  bank_transfer,
                  mobile_money,
                  unassigned,
                  opening_float,
                  actual_cash,
                  actual_card,
                  actual_bank_transfer,
                  actual_mobile_money,
                  actual_unassigned,
                  expected_total,
                  declared_total,
                  variance,
                  status,
                  notes,
                  closed_by,
                  manager_approved_by,
                  manager_approval_reason
                )
                VALUES(
                  :property_code,
                  :business_date,
                  :cashier_name,
                  :cash,
                  :card,
                  :bank_transfer,
                  :mobile_money,
                  :unassigned,
                  :opening_float,
                  :actual_cash,
                  :actual_card,
                  :actual_bank_transfer,
                  :actual_mobile_money,
                  :actual_unassigned,
                  :expected_total,
                  :declared_total,
                  :variance,
                  :status,
                  :notes,
                  :closed_by,
                  :manager_approved_by,
                  :manager_approval_reason
                )
                RETURNING id
                """
            ),
            {
                "property_code": property_code,
                "business_date": payload.business_date,
                "cashier_name": payload.cashier_name.strip(),
                "cash": totals["cash"],
                "card": totals["card"],
                "bank_transfer": totals["bank_transfer"],
                "mobile_money": totals["mobile_money"],
                "unassigned": totals["unassigned"],
                "opening_float": Decimal("0"),
                "actual_cash": actual_totals["cash"],
                "actual_card": actual_totals["card"],
                "actual_bank_transfer": actual_totals["bank_transfer"],
                "actual_mobile_money": actual_totals["mobile_money"],
                "actual_unassigned": actual_totals["unassigned"],
                "expected_total": expected_total,
                "declared_total": declared_total,
                "variance": variance,
                "status": "closed" if abs(variance) < Decimal("0.01") else "variance_review",
                "notes": payload.notes,
                "closed_by": actor["email"],
                "manager_approved_by": manager_approved_by,
                "manager_approval_reason": manager_approval_reason or None,
            },
        ).first()

        record_audit_log(
            db,
            action="cashier_session_closed",
            entity_type="cashier_session",
            entity_id=int(created.id),
            property_code=property_code,
            business_date=payload.business_date,
            details={
                "cashier_name": payload.cashier_name.strip(),
                "expected_total": str(expected_total),
                "declared_total": str(declared_total),
                "variance": str(variance),
                "manager_approved_by": manager_approved_by,
            },
        )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="cashier_session_closed",
            record_type="cashier_session",
            record_id=int(created.id),
            new_value={
                "business_date": payload.business_date.isoformat(),
                "cashier_name": payload.cashier_name.strip(),
                "expected_total": str(expected_total),
                "declared_total": str(declared_total),
                "variance": str(variance),
                "manager_approved_by": manager_approved_by,
            },
        )
        db.commit()

        return {
            "ok": True,
            "session_id": int(created.id),
            "property_code": property_code,
            "business_date": payload.business_date.isoformat(),
            "cashier_name": payload.cashier_name.strip(),
            "expected_total": float(expected_total),
            "declared_total": float(declared_total),
            "variance": float(variance),
            "unassigned": float(totals["unassigned"]),
            "status": "closed" if abs(variance) < Decimal("0.01") else "variance_review",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Close cashier session failed: {e}")


@router.post("/cashier/open")
def open_cashier_session(
    payload: CashierOpenIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_payment",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="open_cashier",
    )

    try:
        created = open_cashier_shift_service(db, property_code=property_code, business_date=payload.business_date, cashier_name=payload.cashier_name, assigned_user_email=actor["email"], opening_float=payload.opening_float, currency="ETB", actor=actor["email"], notes=payload.notes)
        db.commit()
        return {"ok": True, "session_id": int(created["id"]), "status": created["status"], "opening_float": float(created["opening_float"])}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Open cashier session failed: {exc}")

    try:
        _ensure_cashier_sessions_table(db)
        created = db.execute(
            text(
                """
                INSERT INTO cashier_sessions(
                  property_code,
                  business_date,
                  cashier_name,
                  opening_float,
                  expected_total,
                  declared_total,
                  variance,
                  status,
                  notes,
                  opened_at
                )
                VALUES(
                  :property_code,
                  :business_date,
                  :cashier_name,
                  :opening_float,
                  0,
                  0,
                  0,
                  'open',
                  :notes,
                  NOW()
                )
                RETURNING id
                """
            ),
            {
                "property_code": property_code,
                "business_date": payload.business_date,
                "cashier_name": payload.cashier_name.strip(),
                "opening_float": payload.opening_float,
                "notes": payload.notes,
            },
        ).first()
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="cashier_session_opened",
            record_type="cashier_session",
            record_id=int(created.id),
            new_value={
                "business_date": payload.business_date.isoformat(),
                "cashier_name": payload.cashier_name.strip(),
                "opening_float": str(payload.opening_float),
            },
        )
        db.commit()
        return {
            "ok": True,
            "session_id": int(created.id),
            "status": "open",
            "opening_float": float(payload.opening_float),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Open cashier session failed: {e}")


@router.get("/folio/summary")
def get_folio_summary(
    property_code: str,
    booking_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    try:
        property_code = _normalize_property_code(property_code)
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
        folio_id = _get_or_create_folio(db, property_code, int(booking_id))
        _ensure_multi_currency_transaction_columns(db)
        refresh_folio_totals(db, folio_id)
        db.commit()

        row = db.execute(
            text(
                """
                SELECT
                  f.booking_id,
                  f.property_code,
                  f.guest_name,
                  f.currency,
                  COALESCE(f.total_charges, 0) AS charges_total,
                  COALESCE(f.total_payments, 0) AS payments_total,
                  COALESCE(f.balance, 0) AS balance,
                  b.room_number,
                  b.booking_status,
                  b.check_in_date,
                  b.check_out_date
                FROM folios f
                LEFT JOIN bookings b
                  ON b.id = f.booking_id
                 AND b.property_code = f.property_code
                WHERE f.id = :folio_id
                """
            ),
            {"folio_id": folio_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Folio not found")

        return {
            "booking_id": row["booking_id"],
            "property_code": row["property_code"],
            "guest_name": row["guest_name"],
            "room_number": row["room_number"],
            "currency": row["currency"],
            "charges_total": float(row["charges_total"] or 0),
            "payments_total": float(row["payments_total"] or 0),
            "balance": float(row["balance"] or 0),
            "booking_status": row["booking_status"],
            "check_in_date": row["check_in_date"].isoformat() if row["check_in_date"] else None,
            "check_out_date": row["check_out_date"].isoformat() if row["check_out_date"] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Load folio summary failed: {e}")


@router.get("/folio/transactions")
def get_folio_transactions(
    property_code: str,
    booking_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    try:
        property_code = _normalize_property_code(property_code)
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
        folio_id = _get_or_create_folio(db, property_code, int(booking_id))
        _ensure_multi_currency_transaction_columns(db)
        db.commit()

        rows = db.execute(
            text(
                """
                SELECT
                  id,
                  txn_type,
                  business_date AS posting_date,
                  description,
                  category,
                  amount,
                  currency,
                  original_amount,
                  original_currency,
                  exchange_rate_to_base,
                  base_amount,
                  base_currency,
                  exchange_rate_source,
                  exchange_rate_overridden,
                  exchange_rate_override_reason,
                  reference
                FROM folio_transactions
                WHERE folio_id = :folio_id
                ORDER BY id DESC
                """
            ),
            {"folio_id": folio_id},
        ).mappings().all()

        return [
            {
                "id": row["id"],
                "txn_type": row["txn_type"],
                "posting_date": row["posting_date"],
                "description": row["description"],
                "reference": None,
                "category": row["category"],
                "payment_method": row["category"] if row["txn_type"] == "payment" else None,
                "amount": float(row["amount"] or 0),
                "currency": row["currency"],
                "original_amount": float(row["original_amount"] or row["amount"] or 0),
                "original_currency": row["original_currency"] or row["currency"],
                "exchange_rate_to_base": float(row["exchange_rate_to_base"]) if row["exchange_rate_to_base"] is not None else None,
                "base_amount": float(row["base_amount"]) if row["base_amount"] is not None else None,
                "base_currency": row["base_currency"] or _base_currency_for_property(property_code),
                "exchange_rate_source": row["exchange_rate_source"],
                "exchange_rate_overridden": bool(row["exchange_rate_overridden"]),
                "exchange_rate_override_reason": row["exchange_rate_override_reason"],
                "created_at": None,
            }
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Load folio transactions failed: {e}")


@router.get("/checkout/validate")
def validate_checkout(
    property_code: str,
    booking_id: int,
    business_date: date | None = None,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    try:
        property_code = _normalize_property_code(property_code)
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
        folio_id = _get_or_create_folio(db, property_code, int(booking_id))
        refresh_folio_totals(db, folio_id)
        row = db.execute(
            text(
                """
                SELECT
                  COALESCE(balance, 0) AS balance,
                  COALESCE(currency, 'ETB') AS currency,
                  COALESCE(status, 'open') AS status
                FROM folios
                WHERE id = :folio_id
                """
            ),
            {"folio_id": folio_id},
        ).mappings().first()
        booking = _get_booking(db, property_code, int(booking_id))
        db.commit()

        balance = float(row["balance"] or 0) if row else 0.0
        can_checkout = abs(balance) < 0.01
        scheduled_checkout = booking.get("check_out_date")
        checkout_request_date = business_date or date.today()
        is_early_checkout = bool(
            scheduled_checkout and checkout_request_date < scheduled_checkout
        )
        nights_remaining = (
            max((scheduled_checkout - checkout_request_date).days, 0)
            if scheduled_checkout
            else 0
        )
        return {
            "booking_id": int(booking_id),
            "property_code": property_code,
            "balance": balance,
            "currency": row["currency"] if row else "ETB",
            "can_checkout": can_checkout,
            "checkout_request_date": checkout_request_date.isoformat(),
            "scheduled_check_out_date": scheduled_checkout.isoformat() if scheduled_checkout else None,
            "is_early_checkout": is_early_checkout,
            "nights_remaining": nights_remaining,
            "message": "Folio is balanced." if can_checkout else "Folio balance must be settled before checkout.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout validation failed: {e}")


@router.post("/charges")
def post_charge_alias(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    charge = PostChargeIn(
        property_code=payload.get("property_code", ""),
        booking_id=int(payload.get("booking_id", 0)),
        business_date=payload.get("business_date") or date.today(),
        category=payload.get("category") or "misc",
        description=payload.get("description") or payload.get("reference") or "Charge",
        amount=payload.get("amount", 0),
        currency=payload.get("currency") or "ETB",
        reference=payload.get("reference"),
        idempotency_key=payload.get("idempotency_key"),
    )
    return post_charge(charge, db, x_pms_user_email)


@router.post("/payments")
def post_payment_alias(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    payment = PostPaymentIn(
        property_code=payload.get("property_code", ""),
        booking_id=int(payload.get("booking_id", 0)),
        business_date=payload.get("business_date") or date.today(),
        method=payload.get("payment_method") or payload.get("method") or "cash",
        description=payload.get("description") or payload.get("reference") or "Payment",
        amount=payload.get("amount", 0),
        currency=payload.get("currency") or "ETB",
        exchange_rate_to_base=payload.get("exchange_rate_to_base"),
        exchange_rate_source=payload.get("exchange_rate_source"),
        exchange_rate_overridden=bool(payload.get("exchange_rate_overridden") or False),
        exchange_rate_override_reason=payload.get("exchange_rate_override_reason"),
        idempotency_key=payload.get("idempotency_key"),
    )
    return post_payment(payment, db, x_pms_user_email)


@router.post("/folio/post-charge")
def post_charge(
    payload: PostChargeIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_charge",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="post_charge",
    )
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()

    try:
        _ensure_multi_currency_transaction_columns(db)
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        exchange = _payment_exchange_payload(
            property_code=property_code,
            original_amount=payload.amount,
            original_currency=currency,
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
            transaction_type="charge",
            amount=exchange["base_amount"],
            currency=exchange["base_currency"],
            direction="debit",
            reference=payload.reference or payload.description.strip(),
            source_document_type="folio_charge",
            source_document_id=payload.idempotency_key,
            created_by=actor["email"],
            idempotency_key=payload.idempotency_key or f"charge:{uuid4().hex}",
            metadata={"category": payload.category.strip().lower(), **{k: str(v) for k, v in exchange.items()}},
        )
        if ledger["replayed"]:
            db.commit()
            return {"ok": True, "charge_id": None, "ledger_transaction_id": int(ledger["id"]), "replayed": True}

        row = db.execute(
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
                  'charge',
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
                RETURNING id
                """
            ),
            {
                "folio_id": folio_id,
                "property_code": property_code,
                "business_date": payload.business_date,
                "category": payload.category.strip().lower(),
                "description": payload.description.strip(),
                "amount": payload.amount,
                "currency": currency,
                "booking_id": booking_id,
                "reference": ledger["idempotency_key"],
                **exchange,
            },
        ).first()

        refresh_folio_totals(db, folio_id)
        record_audit_log(
            db,
            action="folio_charge_posted",
            entity_type="booking",
            entity_id=booking_id,
            property_code=property_code,
            business_date=payload.business_date,
            details={
                "folio_id": folio_id,
                "charge_id": int(row.id),
                "amount": str(payload.amount),
                "category": payload.category.strip().lower(),
            },
        )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="folio_charge_posted",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "charge_id": int(row.id),
                "amount": str(payload.amount),
                "category": payload.category.strip().lower(),
            },
        )
        db.commit()

        return {
            "ok": True,
            "charge_id": int(row.id),
            "ledger_transaction_id": int(ledger["id"]),
            "replayed": False,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post charge failed: {e}")


@router.post("/folio/post-payment")
def post_payment(
    payload: PostPaymentIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_payment",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="post_payment",
    )
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()

    try:
        idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else f"payment:{uuid4().hex}"
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        _ensure_multi_currency_transaction_columns(db)
        exchange = _payment_exchange_payload(
            property_code=property_code,
            original_amount=payload.amount,
            original_currency=currency,
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
            payment_method=payload.method,
            reference=payload.description.strip(),
            source_document_type="folio_payment",
            source_document_id=idempotency_key,
            created_by=actor["email"],
            idempotency_key=idempotency_key,
            metadata={k: str(v) for k, v in exchange.items()},
            require_cashier_shift=True,
        )
        if ledger["replayed"]:
            db.commit()
            return {"ok": True, "payment_id": None, "ledger_transaction_id": int(ledger["id"]), "replayed": True}

        row = db.execute(
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
                  payment_method,
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
                  :payment_method,
                  :reference
                )
                RETURNING id
                """
            ),
            {
                "folio_id": folio_id,
                "property_code": property_code,
                "business_date": payload.business_date,
                "category": payload.method,
                "description": f"{payload.method.replace('_', ' ').title()}: {payload.description.strip()}",
                "amount": payload.amount,
                "currency": currency,
                "booking_id": booking_id,
                "payment_method": payload.method,
                "reference": idempotency_key,
                **exchange,
            },
        ).first()

        refresh_folio_totals(db, folio_id)
        record_audit_log(
            db,
            action="folio_payment_posted",
            entity_type="booking",
            entity_id=booking_id,
            property_code=property_code,
            business_date=payload.business_date,
            details={
                "folio_id": folio_id,
                "payment_id": int(row.id),
                "amount": str(payload.amount),
                "original_currency": exchange["original_currency"],
                "exchange_rate_to_base": str(exchange["exchange_rate_to_base"]),
                "base_amount": str(exchange["base_amount"]),
                "base_currency": exchange["base_currency"],
                "method": payload.method,
            },
        )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="folio_payment_posted",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "payment_id": int(row.id),
                "amount": str(payload.amount),
                "original_currency": exchange["original_currency"],
                "exchange_rate_to_base": str(exchange["exchange_rate_to_base"]),
                "base_amount": str(exchange["base_amount"]),
                "base_currency": exchange["base_currency"],
                "method": payload.method,
            },
        )
        db.commit()

        return {
            "ok": True,
            "payment_id": int(row.id),
            "ledger_transaction_id": int(ledger["id"]),
            "replayed": False,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post payment failed: {e}")


@router.post("/folio/apply-tax-service")
def apply_tax_service_charge(
    payload: ApplyTaxServiceIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_charge",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="apply_tax_service",
    )
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()
    tax_amount = (payload.taxable_amount * payload.tax_rate).quantize(Decimal("0.01"))
    service_amount = (payload.taxable_amount * payload.service_rate).quantize(Decimal("0.01"))

    try:
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else f"tax-service:{uuid4().hex}"
        posted_ids: list[int] = []
        ledger_ids: list[int] = []
        for category, description, amount in [
            ("tax", f"Tax {payload.tax_rate * 100}%", tax_amount),
            ("service_charge", f"Service charge {payload.service_rate * 100}%", service_amount),
        ]:
            if amount <= 0:
                continue
            ledger = post_finance_transaction(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                folio_id=folio_id,
                booking_id=booking_id,
                transaction_type="charge",
                amount=amount,
                currency=currency,
                direction="debit",
                reference=description,
                source_document_type="tax_service_charge",
                source_document_id=category,
                created_by=actor["email"],
                idempotency_key=f"{idempotency_key}:{category}",
                metadata={"category": category},
            )
            ledger_ids.append(int(ledger["id"]))
            if ledger["replayed"]:
                continue
            row = db.execute(
                text(
                    """
                    INSERT INTO folio_transactions(
                      folio_id, property_code, business_date, txn_type, category,
                      description, amount, currency, booking_id
                    )
                    VALUES(
                      :folio_id, :property_code, :business_date, 'charge', :category,
                      :description, :amount, :currency, :booking_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "folio_id": folio_id,
                    "property_code": property_code,
                    "business_date": payload.business_date,
                    "category": category,
                    "description": description,
                    "amount": amount,
                    "currency": currency,
                    "booking_id": booking_id,
                },
            ).first()
            posted_ids.append(int(row.id))

        refresh_folio_totals(db, folio_id)
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="tax_service_charge_applied",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "tax_amount": str(tax_amount),
                "service_amount": str(service_amount),
                "transaction_ids": posted_ids,
            },
        )
        db.commit()
        return {
            "ok": True,
            "folio_id": folio_id,
            "transaction_ids": posted_ids,
            "ledger_transaction_ids": ledger_ids,
            "tax_amount": float(tax_amount),
            "service_amount": float(service_amount),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Apply tax/service charge failed: {e}")


@router.post("/folio/post-quote-charges")
def post_quote_charges_to_folio(
    payload: PostQuoteChargesIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_charge",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="post_quote_charges",
    )
    booking_id = int(payload.booking_id)

    try:
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else f"quote-charge:{uuid4().hex}"
        existing_count = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM folio_transactions
                    WHERE folio_id = :folio_id
                    """
                ),
                {"folio_id": folio_id},
            ).scalar()
            or 0
        )
        if existing_count:
            raise HTTPException(
                status_code=409,
                detail="Folio already has posted transactions; quote posting is only allowed for empty folios.",
            )

        quote = _booking_quote_for_folio(db, property_code, booking_id)
        tax_rule = _active_tax_service_rule(db, property_code)
        currency = (payload.currency or quote["currency"] or "ETB").strip().upper()
        room_charge = (
            payload.room_charge_amount.quantize(Decimal("0.01"))
            if payload.room_charge_amount is not None
            else quote["room_charge"]
        )
        if room_charge <= 0:
            raise HTTPException(status_code=400, detail="Room charge must be greater than zero.")

        service_rate = Decimal(str(tax_rule["service_charge_percent"] or 0))
        tax_rate = Decimal(str(tax_rule["tax_percent"] or 0))
        service_amount = (room_charge * service_rate).quantize(Decimal("0.01"))
        tax_amount = ((room_charge + service_amount) * tax_rate).quantize(Decimal("0.01"))

        posted_ids: list[int] = []
        ledger_ids: list[int] = []
        for category, description, amount in [
            ("room", f"Room charge from reservation quote ({quote['nights']} night(s))", room_charge),
            ("service_charge", f"Service charge from quote {service_rate * 100}%", service_amount),
            ("tax", f"VAT/Tax from quote {tax_rate * 100}%", tax_amount),
        ]:
            if amount <= 0:
                continue
            ledger = post_finance_transaction(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                folio_id=folio_id,
                booking_id=booking_id,
                transaction_type="charge",
                amount=amount,
                currency=currency,
                direction="debit",
                reference=description,
                source_document_type="reservation_quote_charge",
                source_document_id=category,
                created_by=actor["email"],
                idempotency_key=f"{idempotency_key}:{category}",
                metadata={"category": category},
            )
            ledger_ids.append(int(ledger["id"]))
            if ledger["replayed"]:
                continue
            row = db.execute(
                text(
                    """
                    INSERT INTO folio_transactions(
                      folio_id, property_code, business_date, txn_type, category,
                      description, amount, currency, booking_id
                    )
                    VALUES(
                      :folio_id, :property_code, :business_date, 'charge', :category,
                      :description, :amount, :currency, :booking_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "folio_id": folio_id,
                    "property_code": property_code,
                    "business_date": payload.business_date,
                    "category": category,
                    "description": description,
                    "amount": amount,
                    "currency": currency,
                    "booking_id": booking_id,
                },
            ).first()
            posted_ids.append(int(row.id))

        refresh_folio_totals(db, folio_id)
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="room_charge_posted_from_quote",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "room_charge": str(room_charge),
                "currency": currency,
                "transaction_ids": posted_ids,
            },
        )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="tax_service_posted_from_quote",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "service_charge": str(service_amount),
                "tax": str(tax_amount),
                "service_charge_percent": str(service_rate),
                "tax_percent": str(tax_rate),
                "tax_rule_source": tax_rule["source"],
                "transaction_ids": posted_ids,
            },
        )
        db.commit()
        return {
            "ok": True,
            "folio_id": folio_id,
            "transaction_ids": posted_ids,
            "ledger_transaction_ids": ledger_ids,
            "room_charge": float(room_charge),
            "service_charge": float(service_amount),
            "tax": float(tax_amount),
            "currency": currency,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post quote charges failed: {e}")


@router.post("/folio/void-transaction")
def void_folio_transaction(
    payload: VoidTransactionIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.void_transaction",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="void_transaction",
    )

    try:
        _ensure_folio_accounting_columns(db)
        original = db.execute(
            text(
                """
                SELECT id, folio_id, booking_id, txn_type, category, description, amount, currency, reference
                FROM folio_transactions
                WHERE id = :transaction_id
                  AND property_code = :property_code
                LIMIT 1
                """
            ),
            {"transaction_id": payload.transaction_id, "property_code": property_code},
        ).mappings().first()
        if not original:
            raise HTTPException(status_code=404, detail="Folio transaction not found.")
        if original["txn_type"] not in {"charge", "payment"}:
            raise HTTPException(status_code=409, detail="Only charge or payment transactions can be voided.")

        existing_reversal = db.execute(
            text(
                """
                SELECT id FROM folio_transactions
                WHERE property_code = :property_code
                  AND original_transaction_id = :transaction_id
                LIMIT 1
                """
            ),
            {"property_code": property_code, "transaction_id": payload.transaction_id},
        ).first()
        if existing_reversal:
            raise HTTPException(status_code=409, detail="Folio transaction is already reversed.")
        original_ledger = db.execute(
            text(
                """
                SELECT id FROM finance_transactions
                WHERE property_code = :property_code
                  AND idempotency_key = :idempotency_key
                LIMIT 1
                """
            ),
            {"property_code": property_code, "idempotency_key": original.get("reference")},
        ).first()
        if not original_ledger:
            original_ledger_row = post_finance_transaction(
                db,
                property_code=property_code,
                business_date=payload.business_date,
                folio_id=int(original["folio_id"]),
                booking_id=int(original["booking_id"]) if original["booking_id"] else None,
                transaction_type=original["txn_type"],
                amount=abs(_as_decimal(original["amount"])),
                currency=original["currency"] or "ETB",
                direction="debit" if original["txn_type"] == "charge" else "credit",
                reference=f"Legacy folio transaction #{original['id']} registered before reversal",
                source_document_type="legacy_folio_transaction",
                source_document_id=original["id"],
                created_by=actor["email"],
                idempotency_key=f"legacy-folio:{property_code}:{original['id']}",
                metadata={"legacy_registration": True},
            )
            original_ledger_id = int(original_ledger_row["id"])
        else:
            original_ledger_id = int(original_ledger.id)
        ledger_reversal = reverse_finance_transaction(
            db,
            property_code=property_code,
            transaction_id=original_ledger_id,
            business_date=payload.business_date,
            reversal_type="void",
            reason=payload.reason.strip(),
            created_by=actor["email"],
            idempotency_key=payload.idempotency_key or f"void:{property_code}:{payload.transaction_id}",
            require_cashier_shift=True,
        )

        reversal = db.execute(
            text(
                """
                INSERT INTO folio_transactions(
                  folio_id, property_code, business_date, txn_type, category, description,
                  amount, currency, booking_id, original_transaction_id
                )
                VALUES(
                  :folio_id, :property_code, :business_date, :txn_type, :category,
                  :description, :amount, :currency, :booking_id, :original_transaction_id
                )
                RETURNING id
                """
            ),
            {
                "folio_id": original["folio_id"],
                "property_code": property_code,
                "business_date": payload.business_date,
                "txn_type": original["txn_type"],
                "category": f"void_{original['category'] or 'folio'}",
                "description": f"Void #{original['id']}: {payload.reason.strip()}",
                "amount": -_as_decimal(original["amount"]),
                "currency": original["currency"] or "ETB",
                "booking_id": original["booking_id"],
                "original_transaction_id": original["id"],
            },
        ).first()
        refresh_folio_totals(db, int(original["folio_id"]))
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="folio_transaction_voided",
            record_type="folio_transaction",
            record_id=payload.transaction_id,
            old_value={"amount": str(original["amount"]), "txn_type": original["txn_type"]},
            new_value={
                "reversal_transaction_id": int(reversal.id),
                "ledger_reversal_transaction_id": int(ledger_reversal["id"]),
                "reason": payload.reason.strip(),
            },
        )
        db.commit()
        return {
            "ok": True,
            "transaction_id": payload.transaction_id,
            "reversal_transaction_id": int(reversal.id),
            "ledger_reversal_transaction_id": int(ledger_reversal["id"]),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Void transaction failed: {e}")


@router.post("/folio/refund")
def post_refund(
    payload: RefundIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.void_transaction",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()

    try:
        idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else f"refund:{uuid4().hex}"
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        ledger = post_finance_transaction(
            db,
            property_code=property_code,
            business_date=payload.business_date,
            folio_id=folio_id,
            booking_id=booking_id,
            transaction_type="refund",
            amount=payload.amount,
            currency=currency,
            direction="debit",
            payment_method=payload.method,
            reference=payload.reason.strip(),
            source_document_type="folio_refund",
            source_document_id=idempotency_key,
            created_by=actor["email"],
            idempotency_key=idempotency_key,
            require_cashier_shift=True,
        )
        if ledger["replayed"]:
            db.commit()
            return {"ok": True, "refund_id": None, "ledger_transaction_id": int(ledger["id"]), "replayed": True}
        row = db.execute(
            text(
                """
                INSERT INTO folio_transactions(
                  folio_id, property_code, business_date, txn_type, category,
                  description, amount, currency, booking_id, reference
                )
                VALUES(
                  :folio_id, :property_code, :business_date, 'refund', :category,
                  :description, :amount, :currency, :booking_id, :reference
                )
                RETURNING id
                """
            ),
            {
                "folio_id": folio_id,
                "property_code": property_code,
                "business_date": payload.business_date,
                "category": payload.method,
                "description": f"Refund: {payload.reason.strip()}",
                "amount": payload.amount,
                "currency": currency,
                "booking_id": booking_id,
                "reference": idempotency_key,
            },
        ).first()
        refresh_folio_totals(db, folio_id)
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="folio_refund_posted",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "refund_id": int(row.id),
                "amount": str(payload.amount),
                "method": payload.method,
                "reason": payload.reason.strip(),
            },
        )
        db.commit()
        return {
            "ok": True,
            "refund_id": int(row.id),
            "ledger_transaction_id": int(ledger["id"]),
            "replayed": False,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post refund failed: {e}")


@router.get("/ledger")
def list_finance_transactions(
    property_code: str = Query(..., min_length=1),
    business_date: date | None = Query(None),
    folio_id: int | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    clauses = ["property_code = :property_code"]
    params: dict[str, Any] = {"property_code": property_code}
    if business_date:
        clauses.append("business_date = :business_date")
        params["business_date"] = business_date
    if folio_id:
        clauses.append("folio_id = :folio_id")
        params["folio_id"] = folio_id
    rows = db.execute(
        text(f"SELECT * FROM finance_transactions WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT 500"),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/ledger/adjust")
def post_finance_adjustment(
    payload: AdjustmentIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.post_charge",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="post_adjustment",
    )
    try:
        ledger = post_finance_transaction(
            db,
            property_code=property_code,
            business_date=payload.business_date,
            folio_id=payload.folio_id,
            booking_id=payload.booking_id,
            account_reference=payload.account_reference,
            transaction_type="adjustment",
            amount=payload.amount,
            currency=payload.currency,
            direction=payload.direction,
            reference=payload.reason,
            source_document_type="manual_adjustment",
            created_by=actor["email"],
            idempotency_key=payload.idempotency_key,
        )
        db.commit()
        return {"ok": True, "ledger_transaction_id": int(ledger["id"]), "replayed": ledger["replayed"]}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post adjustment failed: {exc}")


@router.post("/ledger/correct")
def correct_finance_transaction(
    payload: CorrectionIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.void_transaction",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    assert_business_date_editable(
        db,
        property_code=property_code,
        business_date=payload.business_date,
        module="finance",
        action="correct_transaction",
    )
    try:
        original = get_finance_transaction(
            db,
            transaction_id=payload.transaction_id,
            property_code=property_code,
        )
        reversal = reverse_finance_transaction(
            db,
            property_code=property_code,
            transaction_id=payload.transaction_id,
            business_date=payload.business_date,
            reversal_type="correction",
            reason=payload.reason.strip(),
            created_by=actor["email"],
            idempotency_key=f"{payload.idempotency_key}:reversal",
        )
        replacement = post_finance_transaction(
            db,
            property_code=property_code,
            business_date=payload.business_date,
            folio_id=original.get("folio_id"),
            booking_id=original.get("booking_id"),
            account_reference=original.get("account_reference"),
            transaction_type="correction",
            amount=payload.corrected_amount,
            currency=original["currency"],
            direction=original["direction"],
            payment_method=original.get("payment_method"),
            reference=payload.reference or payload.reason.strip(),
            source_document_type="finance_transaction_correction",
            source_document_id=payload.transaction_id,
            created_by=actor["email"],
            idempotency_key=f"{payload.idempotency_key}:replacement",
            metadata={
                "corrects_transaction_id": payload.transaction_id,
                "original_transaction_type": original["transaction_type"],
                "reason": payload.reason.strip(),
            },
        )
        operational_type = {
            "charge": "charge",
            "payment": "payment",
            "deposit": "payment",
            "refund": "refund",
        }.get(original["transaction_type"])
        if original.get("folio_id") and operational_type and not replacement["replayed"]:
            _ensure_folio_accounting_columns(db)
            for amount, category, description, reference in [
                (
                    -_as_decimal(original["amount"]),
                    "correction_reversal",
                    f"Correction reversal for ledger #{payload.transaction_id}: {payload.reason.strip()}",
                    f"{payload.idempotency_key}:reversal",
                ),
                (
                    payload.corrected_amount,
                    "corrected_entry",
                    payload.reference or f"Corrected ledger #{payload.transaction_id}: {payload.reason.strip()}",
                    f"{payload.idempotency_key}:replacement",
                ),
            ]:
                db.execute(
                    text(
                        """
                        INSERT INTO folio_transactions (
                          folio_id, property_code, business_date, txn_type, category,
                          description, amount, currency, booking_id, reference
                        ) VALUES (
                          :folio_id, :property_code, :business_date, :txn_type, :category,
                          :description, :amount, :currency, :booking_id, :reference
                        )
                        """
                    ),
                    {
                        "folio_id": original["folio_id"],
                        "property_code": property_code,
                        "business_date": payload.business_date,
                        "txn_type": operational_type,
                        "category": category,
                        "description": description,
                        "amount": amount,
                        "currency": original["currency"],
                        "booking_id": original.get("booking_id"),
                        "reference": reference,
                    },
                )
            refresh_folio_totals(db, int(original["folio_id"]))
        db.commit()
        return {
            "ok": True,
            "original_transaction_id": payload.transaction_id,
            "reversal_transaction_id": int(reversal["id"]),
            "corrected_transaction_id": int(replacement["id"]),
            "replayed": bool(reversal["replayed"] and replacement["replayed"]),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Correct transaction failed: {exc}")


@router.post("/folio/transfer-balance")
def transfer_folio_balance(
    payload: TransferBalanceIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="finance.transfer_balance",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    booking_id = int(payload.booking_id)
    assert_business_date_editable(db, property_code=property_code, business_date=payload.business_date, module="finance", action="city_ledger_transfer")
    account = db.execute(text("SELECT id FROM ar_company_accounts WHERE property_code=:code AND account_code=:account"), {"code": property_code, "account": payload.billing_account.strip().upper()}).first()
    if not account:
        raise HTTPException(status_code=409, detail="Select a configured City Ledger company account before transferring a folio.")
    try:
        result = transfer_folio_to_ar(db, property_code=property_code, booking_id=booking_id, company_account_id=int(account.id), business_date=payload.business_date, tax=Decimal("0"), actor=actor["email"], idempotency_key=payload.idempotency_key or f"transfer:{property_code}:{booking_id}:{account.id}", manager_override_reason=payload.reason)
        db.commit()
        return {"ok": True, "folio_id": result["folio_id"], "booking_id": booking_id, "balance": float(result["total"]), "billing_account": payload.billing_account.strip().upper(), "status": "transferred_to_billing", "ledger_transaction_id": int(result["ledger_transaction_id"]), "invoice_id": int(result["id"]), "invoice_number": result["invoice_number"], "replayed": result["replayed"]}
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail=f"Transfer balance failed: {exc}")

    try:
        _ensure_folio_accounting_columns(db)
        folio_id = _get_or_create_folio(db, property_code, booking_id)
        refresh_folio_totals(db, folio_id)
        folio = db.execute(
            text(
                """
                SELECT COALESCE(balance, 0) AS balance
                FROM folios
                WHERE id = :folio_id
                """
            ),
            {"folio_id": folio_id},
        ).mappings().first()
        balance = _as_decimal(folio["balance"] if folio else 0)
        if abs(balance) < Decimal("0.01"):
            raise HTTPException(status_code=409, detail="No folio balance exists to transfer.")
        ledger = post_finance_transaction(
            db,
            property_code=property_code,
            business_date=payload.business_date,
            folio_id=folio_id,
            booking_id=booking_id,
            account_reference=payload.billing_account.strip(),
            transaction_type="transfer",
            amount=abs(balance),
            currency=_base_currency_for_property(property_code),
            direction="credit" if balance > 0 else "debit",
            reference=payload.reason.strip(),
            source_document_type="city_ledger_transfer",
            source_document_id=payload.billing_account.strip(),
            created_by=actor["email"],
            idempotency_key=payload.idempotency_key or f"transfer:{property_code}:{folio_id}:{payload.billing_account.strip()}",
        )
        if ledger["replayed"]:
            db.commit()
            return {
                "ok": True,
                "folio_id": folio_id,
                "booking_id": booking_id,
                "balance": float(balance),
                "billing_account": payload.billing_account.strip(),
                "status": "transferred_to_billing",
                "ledger_transaction_id": int(ledger["id"]),
                "replayed": True,
            }

        db.execute(
            text(
                """
                UPDATE folios
                SET status = 'transferred_to_billing',
                    transferred_to = :billing_account,
                    transfer_reason = :reason,
                    transferred_at = NOW()
                WHERE id = :folio_id
                """
            ),
            {
                "folio_id": folio_id,
                "billing_account": payload.billing_account.strip(),
                "reason": payload.reason.strip(),
            },
        )
        booking_columns = _table_columns(db, "bookings")
        if "payment_status" in booking_columns:
            db.execute(
                text(
                    """
                    UPDATE bookings
                    SET payment_status = 'city_ledger'
                    WHERE property_code = :property_code
                      AND id = :booking_id
                    """
                ),
                {"property_code": property_code, "booking_id": booking_id},
            )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="finance",
            action="folio_balance_transferred",
            record_type="booking",
            record_id=booking_id,
            new_value={
                "folio_id": folio_id,
                "balance": str(balance),
                "billing_account": payload.billing_account.strip(),
                "reason": payload.reason.strip(),
            },
        )
        db.commit()
        return {
            "ok": True,
            "folio_id": folio_id,
            "booking_id": booking_id,
            "balance": float(balance),
            "billing_account": payload.billing_account.strip(),
            "status": "transferred_to_billing",
            "ledger_transaction_id": int(ledger["id"]),
            "replayed": False,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transfer balance failed: {e}")


@router.get("/folio/receipt")
def get_folio_receipt(
    property_code: str,
    booking_id: int,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    try:
        property_code = _normalize_property_code(property_code)
        require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
        folio_id = _get_or_create_folio(db, property_code, int(booking_id))
        refresh_folio_totals(db, folio_id)
        booking = _get_booking(db, property_code, int(booking_id))
        folio = db.execute(
            text(
                """
                SELECT id, guest_name, currency, total_charges, total_payments, balance, status
                FROM folios
                WHERE id = :folio_id
                """
            ),
            {"folio_id": folio_id},
        ).mappings().first()
        rows = db.execute(
            text(
                """
                SELECT
                  id,
                  txn_type,
                  category,
                  description,
                  amount,
                  currency,
                  payment_method,
                  reference,
                  business_date,
                  original_amount,
                  original_currency,
                  exchange_rate_to_base,
                  base_amount,
                  base_currency,
                  exchange_rate_source,
                  exchange_rate_overridden,
                  exchange_rate_override_reason
                FROM folio_transactions
                WHERE folio_id = :folio_id
                ORDER BY id
                """
            ),
            {"folio_id": folio_id},
        ).mappings().all()
        charges = [
            dict(row) | {"amount": float(row["amount"] or 0)}
            for row in rows
            if row["txn_type"] == "charge"
        ]
        payments = [
            dict(row)
            | {
                "amount": float(row["amount"] or 0),
                "original_amount": float(row["original_amount"] or row["amount"] or 0),
                "original_currency": row["original_currency"] or row["currency"],
                "exchange_rate_to_base": float(row["exchange_rate_to_base"]) if row["exchange_rate_to_base"] is not None else None,
                "base_amount": float(row["base_amount"]) if row["base_amount"] is not None else None,
                "base_currency": row["base_currency"] or _base_currency_for_property(property_code),
            }
            for row in rows
            if row["txn_type"] in {"payment", "refund"}
        ]
        line_items = [
            {
                "id": row["id"],
                "date": row["business_date"].isoformat() if row["business_date"] else None,
                "txn_type": row["txn_type"],
                "description": row["description"],
                "category": row["category"],
                "amount": float(row["amount"] or 0),
                "currency": row["currency"] or (folio or {}).get("currency") or "ETB",
            }
            for row in rows
        ]
        charge_rows = [row for row in rows if row["txn_type"] == "charge"]
        room_charge_subtotal = sum(
            float(row["amount"] or 0)
            for row in charge_rows
            if str(row["category"] or "").lower() in {"room", "room_revenue"}
        )
        service_charge_amount = sum(
            float(row["amount"] or 0)
            for row in charge_rows
            if str(row["category"] or "").lower() == "service_charge"
        )
        vat_tax_amount = sum(
            float(row["amount"] or 0)
            for row in charge_rows
            if str(row["category"] or "").lower() in {"tax", "vat"}
        )
        fnb_other_charge_subtotal = sum(
            float(row["amount"] or 0)
            for row in charge_rows
            if str(row["category"] or "").lower()
            not in {"room", "room_revenue", "tax", "vat", "service_charge"}
        )
        tax_service_charge = service_charge_amount + vat_tax_amount
        tax_rule = _active_tax_service_rule(db, property_code)
        tax_service_posted = bool(service_charge_amount or vat_tax_amount)
        tax_service_warning = None if tax_service_posted else "Tax/service not posted."
        payment_methods = sorted(
            {
                str(row["category"])
                for row in rows
                if row["txn_type"] in {"payment", "refund"} and row["category"]
            }
        )
        db.commit()
        return {
            "receipt_number": f"RCPT-{property_code}-{folio_id:06d}",
            "invoice_number": f"INV-{property_code}-{folio_id:06d}",
            "property_code": property_code,
            "booking_id": int(booking_id),
            "folio_id": folio_id,
            "guest_name": folio["guest_name"] if folio else booking.get("guest_name"),
            "room_number": booking.get("room_number"),
            "check_in_date": booking.get("check_in_date").isoformat() if booking.get("check_in_date") else None,
            "check_out_date": booking.get("check_out_date").isoformat() if booking.get("check_out_date") else None,
            "charges": charges,
            "payments": payments,
            "line_items": line_items,
            "room_charge_subtotal": room_charge_subtotal,
            "fnb_other_charge_subtotal": fnb_other_charge_subtotal,
            "service_charge_amount": service_charge_amount,
            "vat_tax_amount": vat_tax_amount,
            "tax_service_rates": tax_rule,
            "tax_percent": tax_rule["tax_percent"],
            "service_charge_percent": tax_rule["service_charge_percent"],
            "tax_service_posted": tax_service_posted,
            "tax_service_warning": tax_service_warning,
            "tax_service_charge": tax_service_charge,
            "total_charges": float((folio or {}).get("total_charges") or 0),
            "total_payments": float((folio or {}).get("total_payments") or 0),
            "balance": float((folio or {}).get("balance") or 0),
            "payment_method": ", ".join(payment_methods) if payment_methods else None,
            "currency": (folio or {}).get("currency") or "ETB",
            "folio_status": (folio or {}).get("status") or "open",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Load folio receipt failed: {e}")
