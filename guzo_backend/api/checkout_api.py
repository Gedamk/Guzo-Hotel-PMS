from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db, verify_admin_token

router = APIRouter(prefix="/checkout", tags=["Checkout"])

ALLOWED_PAYMENT_METHODS = {
    "cash",
    "telebirr",
    "cbebirr",
    "pos",
    "bank_transfer",
}


class CheckoutProcessIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date

    pay_amount: Decimal = Field(Decimal("0"))
    pay_method: str = Field("cash", min_length=1)
    description: str = Field("Checkout Payment", min_length=1)
    currency: str = Field("ETB", min_length=1)

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


def _get_booking(db: Session, property_code: str, booking_id: int):
    row = db.execute(
        text(
            """
            SELECT
              id,
              hotel_id,
              property_code,
              guest_name,
              COALESCE(currency, 'ETB') AS currency,
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
    return row


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
def checkout_process(payload: CheckoutProcessIn, db: Session = Depends(get_db)):
    property_code = payload.property_code.strip()
    booking_id = int(payload.booking_id)
    pay_amount = _as_decimal(payload.pay_amount)

    try:
        booking = _get_booking(db, property_code, booking_id)
        folio_id = _get_or_create_folio(db, property_code, booking_id)

        effective_currency = (
            payload.currency.strip().upper()
            if payload.currency and payload.currency.strip()
            else str(booking.get("currency") or "ETB").upper()
        )

        if pay_amount > 0:
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
                      booking_id
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
                      :booking_id
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
                },
            )

        refresh_folio_totals(db, folio_id)
        folio = _read_folio_totals(db, folio_id)

        balance = _as_decimal(folio["balance"])

        folio_closed = False
        booking_checked_out = False

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

        refresh_folio_totals(db, folio_id)
        folio = _read_folio_totals(db, folio_id)

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
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout failed: {e}")