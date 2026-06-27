from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.pms_security_service import record_pms_audit_log


TRANSACTION_TYPES = {
    "charge", "payment", "deposit", "refund", "void", "correction", "transfer", "adjustment"
}
Direction = Literal["debit", "credit"]


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _normalized_amount(amount: Decimal | int | float | str) -> Decimal:
    value = Decimal(str(amount)).copy_abs().quantize(Decimal("0.01"))
    if value <= 0:
        raise HTTPException(status_code=400, detail="Finance transaction amount must be greater than zero.")
    return value


def get_finance_transaction(db: Session, *, transaction_id: int, property_code: str) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT * FROM finance_transactions
            WHERE id = :transaction_id AND property_code = :property_code
            LIMIT 1
            """
        ),
        {"transaction_id": transaction_id, "property_code": property_code.strip().upper()},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Finance transaction not found for selected property.")
    return _row_dict(row)


def post_finance_transaction(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    transaction_type: str,
    amount: Decimal | int | float | str,
    currency: str,
    direction: Direction,
    created_by: str,
    idempotency_key: str,
    folio_id: int | None = None,
    booking_id: int | None = None,
    account_reference: str | None = None,
    payment_method: str | None = None,
    reference: str | None = None,
    source_document_type: str | None = None,
    source_document_id: str | int | None = None,
    reversal_of_transaction_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    cashier_session_id: int | None = None,
    require_cashier_shift: bool = False,
    manager_override_reason: str | None = None,
) -> dict[str, Any]:
    property_code = property_code.strip().upper()
    transaction_type = transaction_type.strip().lower()
    idempotency_key = idempotency_key.strip()
    currency = currency.strip().upper()
    if transaction_type not in TRANSACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported finance transaction type: {transaction_type}")
    if direction not in {"debit", "credit"}:
        raise HTTPException(status_code=400, detail="direction must be debit or credit")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="idempotency_key is required.")
    if not (folio_id or booking_id or (account_reference and account_reference.strip())):
        raise HTTPException(status_code=400, detail="folio_id, booking_id, or account_reference is required.")

    normalized_amount = _normalized_amount(amount)
    if require_cashier_shift and cashier_session_id is None:
        from guzo_backend.services.cashier_shift_service import require_open_shift

        shift = require_open_shift(
            db,
            property_code=property_code,
            business_date=business_date,
            actor=created_by,
            manager_override_reason=manager_override_reason,
        )
        cashier_session_id = int(shift["id"]) if shift else None
    existing = db.execute(
        text("SELECT * FROM finance_transactions WHERE property_code = :property_code AND idempotency_key = :key"),
        {"property_code": property_code, "key": idempotency_key},
    ).mappings().first()
    if existing:
        same = (
            existing["transaction_type"] == transaction_type
            and Decimal(str(existing["amount"])) == normalized_amount
            and existing["currency"] == currency
            and existing["direction"] == direction
            and existing["folio_id"] == folio_id
            and existing["booking_id"] == booking_id
        )
        if not same:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different transaction.")
        return {**_row_dict(existing), "replayed": True}

    audit_reference = f"FIN-{uuid4().hex.upper()}"
    row = db.execute(
        text(
            """
            INSERT INTO finance_transactions (
              property_code, business_date, folio_id, booking_id, account_reference,
              transaction_type, amount, currency, direction, payment_method,
              reference, source_document_type, source_document_id,
              reversal_of_transaction_id, created_by, idempotency_key,
              audit_reference, metadata_json
              , cashier_session_id
            ) VALUES (
              :property_code, :business_date, :folio_id, :booking_id, :account_reference,
              :transaction_type, :amount, :currency, :direction, :payment_method,
              :reference, :source_document_type, :source_document_id,
              :reversal_of_transaction_id, :created_by, :idempotency_key,
              :audit_reference, CAST(:metadata_json AS JSONB)
              , :cashier_session_id
            )
            RETURNING *
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "folio_id": folio_id,
            "booking_id": booking_id,
            "account_reference": account_reference.strip() if account_reference else None,
            "transaction_type": transaction_type,
            "amount": normalized_amount,
            "currency": currency,
            "direction": direction,
            "payment_method": payment_method,
            "reference": reference,
            "source_document_type": source_document_type,
            "source_document_id": str(source_document_id) if source_document_id is not None else None,
            "reversal_of_transaction_id": reversal_of_transaction_id,
            "created_by": created_by.strip().lower(),
            "idempotency_key": idempotency_key,
            "audit_reference": audit_reference,
            "metadata_json": json.dumps(metadata or {}, default=str),
            "cashier_session_id": cashier_session_id,
        },
    ).mappings().first()
    created = _row_dict(row)
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=created_by,
        module="finance",
        action="finance_transaction_created",
        record_type="finance_transaction",
        record_id=created["id"],
        new_value={
            "audit_reference": audit_reference,
            "transaction_type": transaction_type,
            "amount": str(normalized_amount),
            "currency": currency,
            "direction": direction,
            "folio_id": folio_id,
            "booking_id": booking_id,
            "reversal_of_transaction_id": reversal_of_transaction_id,
            "source_document_type": source_document_type,
            "source_document_id": source_document_id,
            "cashier_session_id": cashier_session_id,
        },
    )
    return {**created, "replayed": False}


def reverse_finance_transaction(
    db: Session,
    *,
    property_code: str,
    transaction_id: int,
    business_date: date,
    reversal_type: Literal["void", "correction"],
    reason: str,
    created_by: str,
    idempotency_key: str,
    require_cashier_shift: bool = False,
    manager_override_reason: str | None = None,
) -> dict[str, Any]:
    original = get_finance_transaction(db, transaction_id=transaction_id, property_code=property_code)
    return post_finance_transaction(
        db,
        property_code=property_code,
        business_date=business_date,
        folio_id=original.get("folio_id"),
        booking_id=original.get("booking_id"),
        account_reference=original.get("account_reference"),
        transaction_type=reversal_type,
        amount=original["amount"],
        currency=original["currency"],
        direction="credit" if original["direction"] == "debit" else "debit",
        payment_method=original.get("payment_method"),
        reference=reason,
        source_document_type="finance_transaction_reversal",
        source_document_id=transaction_id,
        reversal_of_transaction_id=transaction_id,
        created_by=created_by,
        idempotency_key=idempotency_key,
        metadata={"reason": reason, "original_audit_reference": original["audit_reference"]},
        require_cashier_shift=require_cashier_shift,
        manager_override_reason=manager_override_reason,
    )
