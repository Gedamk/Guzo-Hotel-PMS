from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.finance_transaction_service import (
    get_finance_transaction,
    post_finance_transaction,
    reverse_finance_transaction,
)
from guzo_backend.services.guest_profile_service import queue_guest_notification
from guzo_backend.services.pms_security_service import record_pms_audit_log


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _booking(db: Session, property_code: str, booking_id: int) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, property_code, guest_name, guest_email, guest_phone,
                   check_in_date, booking_status
            FROM bookings
            WHERE id = :booking_id AND property_code = :property_code
            LIMIT 1
            """
        ),
        {"booking_id": booking_id, "property_code": property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for selected property.")
    return dict(row)


def _folio_id(db: Session, property_code: str, booking_id: int, guest_name: str, currency: str) -> int:
    row = db.execute(
        text("SELECT id FROM folios WHERE property_code = :property_code AND booking_id = :booking_id ORDER BY id LIMIT 1"),
        {"property_code": property_code, "booking_id": booking_id},
    ).first()
    if row:
        return int(row.id)
    created = db.execute(
        text(
            """
            INSERT INTO folios (booking_id, property_code, guest_name, currency, status, total_charges, total_payments, balance)
            VALUES (:booking_id, :property_code, :guest_name, :currency, 'open', 0, 0, 0)
            RETURNING id
            """
        ),
        {"booking_id": booking_id, "property_code": property_code, "guest_name": guest_name, "currency": currency},
    ).first()
    return int(created.id)


def _refresh_folio(db: Session, folio_id: int) -> None:
    totals = db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN txn_type = 'charge' THEN amount ELSE 0 END), 0) charges,
              COALESCE(SUM(CASE WHEN txn_type = 'payment' THEN amount ELSE 0 END), 0) payments
            FROM folio_transactions WHERE folio_id = :folio_id
            """
        ),
        {"folio_id": folio_id},
    ).mappings().first()
    charges, payments = _money(totals["charges"]), _money(totals["payments"])
    db.execute(
        text("UPDATE folios SET total_charges=:charges,total_payments=:payments,balance=:balance WHERE id=:folio_id"),
        {"folio_id": folio_id, "charges": charges, "payments": payments, "balance": charges - payments},
    )


def _deposit_account(db: Session, property_code: str, account_id: int, *, lock: bool = True) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = db.execute(
        text(f"SELECT * FROM deposit_accounts WHERE id=:id AND property_code=:property_code{suffix}"),
        {"id": account_id, "property_code": property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Deposit account not found for selected property.")
    return dict(row)


def _available_deposit(account: dict[str, Any]) -> Decimal:
    return max(
        _money(account["paid_amount"])
        - _money(account["transferred_amount"])
        - _money(account["refunded_amount"])
        - _money(account["forfeited_amount"]),
        Decimal("0.00"),
    )


def _account_payload(account: dict[str, Any]) -> dict[str, Any]:
    paid = _money(account["paid_amount"])
    required = _money(account["required_amount"])
    account = dict(account)
    account["remaining_amount"] = max(required - paid, Decimal("0.00"))
    account["available_amount"] = _available_deposit(account)
    return account


def _existing_event(db: Session, property_code: str, key: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM deposit_events WHERE property_code=:property_code AND idempotency_key=:key"),
        {"property_code": property_code, "key": key},
    ).mappings().first()
    return dict(row) if row else None


def _validate_event_replay(existing: dict[str, Any], account_id: int) -> None:
    if int(existing["deposit_account_id"]) != int(account_id):
        raise HTTPException(status_code=409, detail="Idempotency key belongs to another deposit account.")


def _event(
    db: Session,
    *,
    property_code: str,
    account_id: int,
    event_type: str,
    amount: Decimal,
    currency: str,
    actor: str,
    idempotency_key: str,
    payment_method: str | None = None,
    reference: str | None = None,
    finance_transaction_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit_reference = f"DEP-{uuid4().hex.upper()}"
    row = db.execute(
        text(
            """
            INSERT INTO deposit_events (
              property_code,deposit_account_id,event_type,amount,currency,payment_method,
              reference,finance_transaction_id,idempotency_key,audit_reference,created_by,metadata_json
            ) VALUES (
              :property_code,:account_id,:event_type,:amount,:currency,:payment_method,
              :reference,:finance_transaction_id,:idempotency_key,:audit_reference,:created_by,
              CAST(:metadata AS JSONB)
            ) RETURNING *
            """
        ),
        {
            "property_code": property_code,
            "account_id": account_id,
            "event_type": event_type,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "reference": reference,
            "finance_transaction_id": finance_transaction_id,
            "idempotency_key": idempotency_key,
            "audit_reference": audit_reference,
            "created_by": actor,
            "metadata": json.dumps(metadata or {}, default=str),
        },
    ).mappings().first()
    return dict(row)


def _audit(db: Session, *, property_code: str, actor: str, action: str, account_id: int, value: dict[str, Any]) -> None:
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor,
        module="finance",
        action=action,
        record_type="deposit_account",
        record_id=account_id,
        new_value=value,
    )


def request_deposit(
    db: Session,
    *,
    property_code: str,
    booking_id: int,
    business_date: date,
    required_amount: Decimal,
    requested_amount: Decimal,
    currency: str,
    refundable: bool,
    actor: str,
    idempotency_key: str,
    reference: str | None = None,
    public_request_id: int | None = None,
) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        return {**_account_payload(_deposit_account(db, property_code, int(existing["deposit_account_id"]), lock=False)), "replayed": True}
    booking = _booking(db, property_code, booking_id)
    required_amount, requested_amount = _money(required_amount), _money(requested_amount)
    if required_amount <= 0 or requested_amount <= 0 or requested_amount > required_amount:
        raise HTTPException(status_code=400, detail="Deposit request amounts must be positive and requested_amount cannot exceed required_amount.")
    row = db.execute(
        text(
            """
            INSERT INTO deposit_accounts (
              property_code,booking_id,public_request_id,business_date,required_amount,
              requested_amount,currency,refundable,status,reference,created_by
            ) VALUES (
              :property_code,:booking_id,:public_request_id,:business_date,:required_amount,
              :requested_amount,:currency,:refundable,'requested',:reference,:actor
            )
            ON CONFLICT (property_code,booking_id) DO UPDATE SET
              required_amount=EXCLUDED.required_amount,
              requested_amount=EXCLUDED.requested_amount,
              refundable=EXCLUDED.refundable,
              reference=EXCLUDED.reference,
              updated_at=CURRENT_TIMESTAMP
            RETURNING *
            """
        ),
        {
            "property_code": property_code,
            "booking_id": booking_id,
            "public_request_id": public_request_id,
            "business_date": business_date,
            "required_amount": required_amount,
            "requested_amount": requested_amount,
            "currency": currency,
            "refundable": refundable,
            "reference": reference,
            "actor": actor,
        },
    ).mappings().first()
    account = dict(row)
    _event(db, property_code=property_code, account_id=account["id"], event_type="requested", amount=requested_amount, currency=currency, actor=actor, idempotency_key=idempotency_key, reference=reference)
    _audit(db, property_code=property_code, actor=actor, action="deposit_requested", account_id=account["id"], value={"requested_amount": str(requested_amount), "required_amount": str(required_amount), "refundable": refundable})
    queue_guest_notification(db, property_code=property_code, booking_id=booking_id, guest_email=booking.get("guest_email"), guest_phone=booking.get("guest_phone"), action="deposit_requested", message=f"Deposit requested: {currency} {requested_amount:.2f}.", business_date=business_date)
    return {**_account_payload(account), "replayed": False}


def receive_deposit(
    db: Session,
    *,
    property_code: str,
    account_id: int,
    business_date: date,
    amount: Decimal,
    payment_method: str,
    reference: str,
    actor: str,
    idempotency_key: str,
    require_cashier_shift: bool = False,
) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        _validate_event_replay(existing, account_id)
        return {**_account_payload(_deposit_account(db, property_code, account_id, lock=False)), "replayed": True, "finance_transaction_id": existing["finance_transaction_id"]}
    account = _deposit_account(db, property_code, account_id)
    amount = _money(amount)
    remaining = max(_money(account["requested_amount"]) - _money(account["paid_amount"]), Decimal("0.00"))
    if amount <= 0 or amount > remaining:
        raise HTTPException(status_code=409, detail=f"Deposit receipt exceeds remaining requested deposit {remaining}.")
    ledger = post_finance_transaction(
        db,
        property_code=property_code,
        business_date=business_date,
        booking_id=account["booking_id"],
        account_reference=f"deposit:{account_id}",
        transaction_type="deposit",
        amount=amount,
        currency=account["currency"],
        direction="credit",
        payment_method=payment_method,
        reference=reference,
        source_document_type="deposit_account",
        source_document_id=account_id,
        created_by=actor,
        idempotency_key=idempotency_key,
        require_cashier_shift=require_cashier_shift,
    )
    paid = _money(account["paid_amount"]) + amount
    status = "paid" if paid >= _money(account["requested_amount"]) else "partial"
    updated = db.execute(
        text("UPDATE deposit_accounts SET paid_amount=:paid,status=:status,payment_method=:method,reference=:reference,updated_at=CURRENT_TIMESTAMP WHERE id=:id AND property_code=:property_code RETURNING *"),
        {"paid": paid, "status": status, "method": payment_method, "reference": reference, "id": account_id, "property_code": property_code},
    ).mappings().first()
    _event(db, property_code=property_code, account_id=account_id, event_type="receipt", amount=amount, currency=account["currency"], actor=actor, idempotency_key=idempotency_key, payment_method=payment_method, reference=reference, finance_transaction_id=ledger["id"])
    _audit(db, property_code=property_code, actor=actor, action="deposit_receipt_recorded", account_id=account_id, value={"amount": str(amount), "paid_amount": str(paid), "status": status, "finance_transaction_id": ledger["id"]})
    booking = _booking(db, property_code, int(account["booking_id"]))
    queue_guest_notification(db, property_code=property_code, booking_id=account["booking_id"], guest_email=booking.get("guest_email"), guest_phone=booking.get("guest_phone"), action="deposit_receipt", message=f"Deposit received: {account['currency']} {amount:.2f}. Reference: {reference}.", business_date=business_date)
    return {**_account_payload(dict(updated)), "replayed": False, "finance_transaction_id": int(ledger["id"])}


def allocate_deposit(db: Session, *, property_code: str, account_id: int, amount: Decimal, actor: str, idempotency_key: str) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        _validate_event_replay(existing, account_id)
        return {**_account_payload(_deposit_account(db, property_code, account_id, lock=False)), "replayed": True}
    account = _deposit_account(db, property_code, account_id)
    amount = _money(amount)
    if amount <= 0 or amount > _available_deposit(account):
        raise HTTPException(status_code=409, detail="Allocated deposit exceeds available deposit.")
    booking = _booking(db, property_code, int(account["booking_id"]))
    folio_id = _folio_id(db, property_code, int(account["booking_id"]), booking["guest_name"], account["currency"])
    allocated = _money(account["allocated_amount"]) + amount
    updated = db.execute(
        text("UPDATE deposit_accounts SET folio_id=:folio_id,allocated_amount=:amount,status='allocated',updated_at=CURRENT_TIMESTAMP WHERE id=:id AND property_code=:property_code RETURNING *"),
        {"folio_id": folio_id, "amount": allocated, "id": account_id, "property_code": property_code},
    ).mappings().first()
    _event(db, property_code=property_code, account_id=account_id, event_type="allocated", amount=amount, currency=account["currency"], actor=actor, idempotency_key=idempotency_key, reference=f"folio:{folio_id}")
    _audit(db, property_code=property_code, actor=actor, action="deposit_allocated", account_id=account_id, value={"amount": str(amount), "folio_id": folio_id})
    return {**_account_payload(dict(updated)), "replayed": False}


def transfer_deposit_to_folio(db: Session, *, property_code: str, account_id: int, business_date: date, amount: Decimal | None, actor: str, idempotency_key: str) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        _validate_event_replay(existing, account_id)
        return {**_account_payload(_deposit_account(db, property_code, account_id, lock=False)), "replayed": True, "finance_transaction_id": existing["finance_transaction_id"]}
    account = _deposit_account(db, property_code, account_id)
    available = _available_deposit(account)
    requested = _money(amount) if amount is not None else min(available, _money(account["allocated_amount"]) - _money(account["transferred_amount"]) if _money(account["allocated_amount"]) else available)
    if requested <= 0 or requested > available:
        raise HTTPException(status_code=409, detail="Deposit transfer exceeds available deposit.")
    booking = _booking(db, property_code, int(account["booking_id"]))
    folio_id = int(account["folio_id"] or _folio_id(db, property_code, int(account["booking_id"]), booking["guest_name"], account["currency"]))
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, folio_id=folio_id, booking_id=account["booking_id"], account_reference=f"deposit:{account_id}", transaction_type="transfer", amount=requested, currency=account["currency"], direction="debit", reference=f"Deposit transferred to folio {folio_id}", source_document_type="deposit_account", source_document_id=account_id, created_by=actor, idempotency_key=idempotency_key)
    db.execute(text("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS reference VARCHAR(160)"))
    folio_txn = db.execute(
        text("INSERT INTO folio_transactions(folio_id,property_code,business_date,txn_type,category,description,amount,currency,booking_id,payment_method,reference) VALUES(:folio_id,:property_code,:business_date,'payment','deposit_transfer','Deposit transferred at check-in',:amount,:currency,:booking_id,:method,:reference) RETURNING id"),
        {"folio_id": folio_id, "property_code": property_code, "business_date": business_date, "amount": requested, "currency": account["currency"], "booking_id": account["booking_id"], "method": account.get("payment_method") or "deposit", "reference": idempotency_key},
    ).first()
    transferred = _money(account["transferred_amount"]) + requested
    updated = db.execute(text("UPDATE deposit_accounts SET folio_id=:folio_id,transferred_amount=:amount,status='transferred',updated_at=CURRENT_TIMESTAMP WHERE id=:id AND property_code=:property_code RETURNING *"), {"folio_id": folio_id, "amount": transferred, "id": account_id, "property_code": property_code}).mappings().first()
    _refresh_folio(db, folio_id)
    _event(db, property_code=property_code, account_id=account_id, event_type="transferred", amount=requested, currency=account["currency"], actor=actor, idempotency_key=idempotency_key, reference=f"folio_transaction:{folio_txn.id}", finance_transaction_id=ledger["id"])
    _audit(db, property_code=property_code, actor=actor, action="deposit_transferred_to_folio", account_id=account_id, value={"amount": str(requested), "folio_id": folio_id, "finance_transaction_id": ledger["id"]})
    return {**_account_payload(dict(updated)), "replayed": False, "finance_transaction_id": int(ledger["id"]), "folio_transaction_id": int(folio_txn.id)}


def refund_deposit(db: Session, *, property_code: str, account_id: int, business_date: date, amount: Decimal, payment_method: str, reason: str, actor: str, idempotency_key: str, require_cashier_shift: bool = False) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        _validate_event_replay(existing, account_id)
        return {**_account_payload(_deposit_account(db, property_code, account_id, lock=False)), "replayed": True, "finance_transaction_id": existing["finance_transaction_id"]}
    account = _deposit_account(db, property_code, account_id)
    if not account["refundable"]:
        raise HTTPException(status_code=409, detail="Deposit is non-refundable.")
    amount = _money(amount)
    available = _available_deposit(account)
    if amount <= 0 or amount > available:
        raise HTTPException(status_code=409, detail=f"Refund exceeds refundable deposit {available}.")
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, booking_id=account["booking_id"], account_reference=f"deposit:{account_id}", transaction_type="refund", amount=amount, currency=account["currency"], direction="debit", payment_method=payment_method, reference=reason, source_document_type="deposit_refund", source_document_id=account_id, created_by=actor, idempotency_key=idempotency_key, require_cashier_shift=require_cashier_shift)
    refunded = _money(account["refunded_amount"]) + amount
    status = "refunded" if refunded >= _money(account["paid_amount"]) else "partially_refunded"
    updated = db.execute(text("UPDATE deposit_accounts SET refunded_amount=:amount,status=:status,updated_at=CURRENT_TIMESTAMP WHERE id=:id AND property_code=:property_code RETURNING *"), {"amount": refunded, "status": status, "id": account_id, "property_code": property_code}).mappings().first()
    _event(db, property_code=property_code, account_id=account_id, event_type="refunded", amount=amount, currency=account["currency"], actor=actor, idempotency_key=idempotency_key, payment_method=payment_method, reference=reason, finance_transaction_id=ledger["id"])
    _audit(db, property_code=property_code, actor=actor, action="deposit_refunded", account_id=account_id, value={"amount": str(amount), "reason": reason, "finance_transaction_id": ledger["id"]})
    return {**_account_payload(dict(updated)), "replayed": False, "finance_transaction_id": int(ledger["id"])}


def forfeit_deposit(db: Session, *, property_code: str, account_id: int, business_date: date, amount: Decimal | None, reason: str, actor: str, idempotency_key: str) -> dict[str, Any]:
    existing = _existing_event(db, property_code, idempotency_key)
    if existing:
        _validate_event_replay(existing, account_id)
        return {**_account_payload(_deposit_account(db, property_code, account_id, lock=False)), "replayed": True}
    account = _deposit_account(db, property_code, account_id)
    available = _available_deposit(account)
    amount = _money(amount) if amount is not None else available
    if amount <= 0 or amount > available:
        raise HTTPException(status_code=409, detail="Forfeiture exceeds available deposit.")
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, booking_id=account["booking_id"], account_reference=f"deposit:{account_id}", transaction_type="adjustment", amount=amount, currency=account["currency"], direction="debit", reference=reason, source_document_type="deposit_forfeiture", source_document_id=account_id, created_by=actor, idempotency_key=idempotency_key)
    forfeited = _money(account["forfeited_amount"]) + amount
    updated = db.execute(text("UPDATE deposit_accounts SET forfeited_amount=:amount,status='forfeited',updated_at=CURRENT_TIMESTAMP WHERE id=:id AND property_code=:property_code RETURNING *"), {"amount": forfeited, "id": account_id, "property_code": property_code}).mappings().first()
    _event(db, property_code=property_code, account_id=account_id, event_type="forfeited", amount=amount, currency=account["currency"], actor=actor, idempotency_key=idempotency_key, reference=reason, finance_transaction_id=ledger["id"])
    _audit(db, property_code=property_code, actor=actor, action="deposit_forfeited", account_id=account_id, value={"amount": str(amount), "reason": reason, "finance_transaction_id": ledger["id"]})
    return {**_account_payload(dict(updated)), "replayed": False, "finance_transaction_id": int(ledger["id"])}


def list_deposits(db: Session, *, property_code: str, booking_id: int | None = None) -> list[dict[str, Any]]:
    clause = " AND booking_id=:booking_id" if booking_id else ""
    params: dict[str, Any] = {"property_code": property_code}
    if booking_id:
        params["booking_id"] = booking_id
    rows = db.execute(text(f"SELECT * FROM deposit_accounts WHERE property_code=:property_code{clause} ORDER BY id DESC"), params).mappings().all()
    return [_account_payload(dict(row)) for row in rows]


def receive_split_payment(
    db: Session,
    *,
    property_code: str,
    booking_id: int,
    business_date: date,
    requested_amount: Decimal,
    currency: str,
    allocations: list[dict[str, Any]],
    reference: str | None,
    actor: str,
    idempotency_key: str,
    require_cashier_shift: bool = False,
) -> dict[str, Any]:
    existing = db.execute(text("SELECT * FROM payment_batches WHERE property_code=:property_code AND idempotency_key=:key"), {"property_code": property_code, "key": idempotency_key}).mappings().first()
    if existing:
        return {**dict(existing), "replayed": True}
    booking = _booking(db, property_code, booking_id)
    requested_amount = _money(requested_amount)
    received_amount = sum((_money(item["amount"]) for item in allocations), Decimal("0.00"))
    if requested_amount <= 0 or received_amount <= 0 or not allocations:
        raise HTTPException(status_code=400, detail="Payment amount and allocations are required.")
    folio_id = _folio_id(db, property_code, booking_id, booking["guest_name"], currency)
    overpayment = max(received_amount - requested_amount, Decimal("0.00"))
    status = "overpaid" if overpayment else "paid" if received_amount == requested_amount else "partial"
    batch = db.execute(text("INSERT INTO payment_batches(property_code,business_date,booking_id,folio_id,requested_amount,received_amount,overpayment_amount,currency,status,reference,idempotency_key,created_by) VALUES(:property_code,:business_date,:booking_id,:folio_id,:requested,:received,:overpayment,:currency,:status,:reference,:key,:actor) RETURNING *"), {"property_code": property_code, "business_date": business_date, "booking_id": booking_id, "folio_id": folio_id, "requested": requested_amount, "received": received_amount, "overpayment": overpayment, "currency": currency, "status": status, "reference": reference, "key": idempotency_key, "actor": actor}).mappings().first()
    ledger_ids: list[int] = []
    for index, allocation in enumerate(allocations):
        amount = _money(allocation["amount"])
        method = str(allocation["payment_method"]).strip().lower()
        ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, folio_id=folio_id, booking_id=booking_id, transaction_type="payment", amount=amount, currency=currency, direction="credit", payment_method=method, reference=allocation.get("reference") or reference, source_document_type="payment_batch", source_document_id=batch["id"], created_by=actor, idempotency_key=f"{idempotency_key}:{index}", require_cashier_shift=require_cashier_shift)
        folio_txn = db.execute(text("INSERT INTO folio_transactions(folio_id,property_code,business_date,txn_type,category,description,amount,currency,booking_id,payment_method,reference) VALUES(:folio_id,:property_code,:business_date,'payment',:method,:description,:amount,:currency,:booking_id,:method,:reference) RETURNING id"), {"folio_id": folio_id, "property_code": property_code, "business_date": business_date, "method": method, "description": f"{method.replace('_',' ').title()} payment receipt", "amount": amount, "currency": currency, "booking_id": booking_id, "reference": allocation.get("reference") or idempotency_key}).first()
        db.execute(text("INSERT INTO payment_allocations(property_code,payment_batch_id,payment_method,amount,reference,finance_transaction_id,folio_transaction_id) VALUES(:property_code,:batch_id,:method,:amount,:reference,:ledger_id,:folio_txn_id)"), {"property_code": property_code, "batch_id": batch["id"], "method": method, "amount": amount, "reference": allocation.get("reference"), "ledger_id": ledger["id"], "folio_txn_id": folio_txn.id})
        ledger_ids.append(int(ledger["id"]))
    _refresh_folio(db, folio_id)
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="payment_receipt_recorded", record_type="payment_batch", record_id=batch["id"], new_value={"requested_amount": str(requested_amount), "received_amount": str(received_amount), "overpayment_amount": str(overpayment), "status": status, "ledger_transaction_ids": ledger_ids})
    queue_guest_notification(db, property_code=property_code, booking_id=booking_id, guest_email=booking.get("guest_email"), guest_phone=booking.get("guest_phone"), action="payment_receipt", message=f"Payment received: {currency} {received_amount:.2f}. Reference: {reference or batch['id']}.", business_date=business_date)
    return {**dict(batch), "ledger_transaction_ids": ledger_ids, "replayed": False}


def refund_payment(db: Session, *, property_code: str, original_transaction_id: int, business_date: date, amount: Decimal, payment_method: str, reason: str, actor: str, idempotency_key: str, require_cashier_shift: bool = False) -> dict[str, Any]:
    original = get_finance_transaction(db, transaction_id=original_transaction_id, property_code=property_code)
    if original["transaction_type"] not in {"payment", "deposit"} or original["direction"] != "credit":
        raise HTTPException(status_code=409, detail="Only received payments or deposits are refundable.")
    refunded = _money(db.execute(text("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE property_code=:property_code AND transaction_type='refund' AND source_document_type='payment_refund' AND source_document_id=:source_id"), {"property_code": property_code, "source_id": str(original_transaction_id)}).scalar())
    amount = _money(amount)
    eligible = _money(original["amount"]) - refunded
    if amount <= 0 or amount > eligible:
        raise HTTPException(status_code=409, detail=f"Refund exceeds eligible amount {eligible}.")
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, folio_id=original.get("folio_id"), booking_id=original.get("booking_id"), account_reference=original.get("account_reference"), transaction_type="refund", amount=amount, currency=original["currency"], direction="debit", payment_method=payment_method, reference=reason, source_document_type="payment_refund", source_document_id=original_transaction_id, created_by=actor, idempotency_key=idempotency_key, require_cashier_shift=require_cashier_shift)
    if original.get("folio_id") and not ledger["replayed"]:
        db.execute(text("INSERT INTO folio_transactions(folio_id,property_code,business_date,txn_type,category,description,amount,currency,booking_id,payment_method,reference) VALUES(:folio_id,:property_code,:business_date,'refund',:method,:description,:amount,:currency,:booking_id,:method,:reference)"), {"folio_id": original["folio_id"], "property_code": property_code, "business_date": business_date, "method": payment_method, "description": f"Refund: {reason}", "amount": amount, "currency": original["currency"], "booking_id": original.get("booking_id"), "reference": idempotency_key})
        _refresh_folio(db, int(original["folio_id"]))
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="payment_refunded", record_type="finance_transaction", record_id=ledger["id"], new_value={"original_transaction_id": original_transaction_id, "amount": str(amount), "eligible_before": str(eligible), "reason": reason})
    return {"ok": True, "finance_transaction_id": int(ledger["id"]), "eligible_remaining": eligible - amount, "replayed": ledger["replayed"]}


def void_payment(db: Session, *, property_code: str, original_transaction_id: int, business_date: date, reason: str, approved_by: str, actor: str, idempotency_key: str, require_cashier_shift: bool = False) -> dict[str, Any]:
    original = get_finance_transaction(db, transaction_id=original_transaction_id, property_code=property_code)
    if original["transaction_type"] != "payment":
        raise HTTPException(status_code=409, detail="Only payment transactions can use payment void approval.")
    refunded = _money(db.execute(text("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE property_code=:property_code AND transaction_type='refund' AND source_document_type='payment_refund' AND source_document_id=:source_id"), {"property_code": property_code, "source_id": str(original_transaction_id)}).scalar())
    if refunded > 0:
        raise HTTPException(status_code=409, detail="Partially refunded payments cannot be voided; correct the remaining balance with ledger reversals.")
    reversal = reverse_finance_transaction(db, property_code=property_code, transaction_id=original_transaction_id, business_date=business_date, reversal_type="void", reason=reason, created_by=actor, idempotency_key=idempotency_key, require_cashier_shift=require_cashier_shift)
    if original.get("folio_id") and not reversal["replayed"]:
        db.execute(text("INSERT INTO folio_transactions(folio_id,property_code,business_date,txn_type,category,description,amount,currency,booking_id,payment_method,reference) VALUES(:folio_id,:property_code,:business_date,'payment','void_payment',:description,:amount,:currency,:booking_id,:method,:reference)"), {"folio_id": original["folio_id"], "property_code": property_code, "business_date": business_date, "description": f"Approved payment void: {reason}", "amount": -_money(original["amount"]), "currency": original["currency"], "booking_id": original.get("booking_id"), "method": original.get("payment_method"), "reference": idempotency_key})
        _refresh_folio(db, int(original["folio_id"]))
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="payment_void_approved", record_type="finance_transaction", record_id=original_transaction_id, new_value={"reversal_transaction_id": reversal["id"], "approved_by": approved_by, "reason": reason})
    return {"ok": True, "reversal_transaction_id": int(reversal["id"]), "approved_by": approved_by, "replayed": reversal["replayed"]}
