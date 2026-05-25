from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db

router = APIRouter(prefix="/finance", tags=["Finance"])

ALLOWED_PAYMENT_METHODS = {
    "cash",
    "telebirr",
    "cbebirr",
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
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    method: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)

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
              property_code,
              guest_name,
              COALESCE(currency, 'ETB') AS currency
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


@router.get("/folio/summary")
def get_folio_summary(
    property_code: str,
    booking_id: int,
    db: Session = Depends(get_db),
):
    try:
        folio_id = _get_or_create_folio(db, property_code.strip(), int(booking_id))
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
                  b.booking_status
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
):
    try:
        folio_id = _get_or_create_folio(db, property_code.strip(), int(booking_id))
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
                  currency
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
                "created_at": None,
            }
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Load folio transactions failed: {e}")


@router.post("/charges")
def post_charge_alias(payload: dict[str, Any], db: Session = Depends(get_db)):
    charge = PostChargeIn(
        property_code=payload.get("property_code", ""),
        booking_id=int(payload.get("booking_id", 0)),
        business_date=date.today(),
        category=payload.get("category") or "misc",
        description=payload.get("description") or payload.get("reference") or "Charge",
        amount=payload.get("amount", 0),
        currency=payload.get("currency") or "ETB",
    )
    return post_charge(charge, db)


@router.post("/payments")
def post_payment_alias(payload: dict[str, Any], db: Session = Depends(get_db)):
    payment = PostPaymentIn(
        property_code=payload.get("property_code", ""),
        booking_id=int(payload.get("booking_id", 0)),
        business_date=date.today(),
        method=payload.get("payment_method") or payload.get("method") or "cash",
        description=payload.get("description") or payload.get("reference") or "Payment",
        amount=payload.get("amount", 0),
        currency=payload.get("currency") or "ETB",
    )
    return post_payment(payment, db)


@router.post("/folio/post-charge")
def post_charge(payload: PostChargeIn, db: Session = Depends(get_db)):
    property_code = payload.property_code.strip()
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()

    try:
        folio_id = _get_or_create_folio(db, property_code, booking_id)

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
                  booking_id
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
                  :booking_id
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
            },
        ).first()

        refresh_folio_totals(db, folio_id)
        db.commit()

        return {"ok": True, "charge_id": int(row.id)}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post charge failed: {e}")


@router.post("/folio/post-payment")
def post_payment(payload: PostPaymentIn, db: Session = Depends(get_db)):
    property_code = payload.property_code.strip()
    booking_id = int(payload.booking_id)
    currency = payload.currency.strip().upper()

    try:
        folio_id = _get_or_create_folio(db, property_code, booking_id)

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
            },
        ).first()

        refresh_folio_totals(db, folio_id)
        db.commit()

        return {"ok": True, "payment_id": int(row.id)}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Post payment failed: {e}")
