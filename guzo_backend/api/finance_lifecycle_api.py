from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.business_date_lock_service import assert_business_date_editable
from guzo_backend.services.payment_lifecycle_service import (
    allocate_deposit,
    forfeit_deposit,
    list_deposits,
    receive_deposit,
    receive_split_payment,
    refund_deposit,
    refund_payment,
    request_deposit,
    transfer_deposit_to_folio,
    void_payment,
)
from guzo_backend.services.pms_security_service import require_pms_permission, require_property_access


router = APIRouter(prefix="/finance", tags=["Finance Lifecycle"])


class DepositRequestIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    required_amount: Decimal = Field(..., gt=0)
    requested_amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)
    refundable: bool = True
    reference: str | None = None
    public_request_id: int | None = None
    idempotency_key: str = Field(..., min_length=3)


class DepositReceiptIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1)
    reference: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=3)


class DepositAllocationIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=3)


class DepositTransferIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    amount: Decimal | None = Field(None, gt=0)
    idempotency_key: str = Field(..., min_length=3)


class DepositRefundIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)


class DepositForfeitIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    amount: Decimal | None = Field(None, gt=0)
    reason: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)


class PaymentAllocationIn(BaseModel):
    payment_method: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    reference: str | None = None


class PaymentReceiptIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    booking_id: int
    business_date: date
    requested_amount: Decimal = Field(..., gt=0)
    currency: str = Field("ETB", min_length=1)
    allocations: list[PaymentAllocationIn] = Field(..., min_length=1)
    reference: str | None = None
    idempotency_key: str = Field(..., min_length=3)


class PaymentRefundIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    original_transaction_id: int
    business_date: date
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)


class PaymentVoidIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    original_transaction_id: int
    business_date: date
    reason: str = Field(..., min_length=3)
    approved_by: str = Field(..., min_length=3)
    idempotency_key: str = Field(..., min_length=3)


def _code(value: str) -> str:
    return value.strip().upper()


def _editable(db: Session, property_code: str, business_date: date, action: str) -> None:
    assert_business_date_editable(db, property_code=property_code, business_date=business_date, module="finance", action=action)


def _finish(db: Session, operation):
    try:
        result = operation()
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Payment lifecycle operation failed: {exc}")


@router.get("/deposits")
def get_deposits(property_code: str = Query(...), booking_id: int | None = Query(None), db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    property_code = _code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return list_deposits(db, property_code=property_code, booking_id=booking_id)


@router.post("/deposits/request")
def create_deposit_request(payload: DepositRequestIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="reservations.modify_booking", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "deposit_request")
    return _finish(db, lambda: request_deposit(db, property_code=code, booking_id=payload.booking_id, business_date=payload.business_date, required_amount=payload.required_amount, requested_amount=payload.requested_amount, currency=payload.currency.upper(), refundable=payload.refundable, actor=actor["email"], idempotency_key=payload.idempotency_key, reference=payload.reference, public_request_id=payload.public_request_id))


@router.post("/deposits/{account_id}/receipt")
def record_deposit_receipt(account_id: int, payload: DepositReceiptIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.record_deposit", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "deposit_receipt")
    return _finish(db, lambda: receive_deposit(db, property_code=code, account_id=account_id, business_date=payload.business_date, amount=payload.amount, payment_method=payload.payment_method, reference=payload.reference, actor=actor["email"], idempotency_key=payload.idempotency_key, require_cashier_shift=True))


@router.post("/deposits/{account_id}/allocate")
def allocate_deposit_to_folio(account_id: int, payload: DepositAllocationIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.record_deposit", property_code=code, user_email=x_pms_user_email)
    return _finish(db, lambda: allocate_deposit(db, property_code=code, account_id=account_id, amount=payload.amount, actor=actor["email"], idempotency_key=payload.idempotency_key))


@router.post("/deposits/{account_id}/transfer")
def transfer_deposit(account_id: int, payload: DepositTransferIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.record_deposit", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "deposit_transfer")
    return _finish(db, lambda: transfer_deposit_to_folio(db, property_code=code, account_id=account_id, business_date=payload.business_date, amount=payload.amount, actor=actor["email"], idempotency_key=payload.idempotency_key))


@router.post("/deposits/{account_id}/refund")
def refund_deposit_endpoint(account_id: int, payload: DepositRefundIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.void_transaction", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "deposit_refund")
    return _finish(db, lambda: refund_deposit(db, property_code=code, account_id=account_id, business_date=payload.business_date, amount=payload.amount, payment_method=payload.payment_method, reason=payload.reason, actor=actor["email"], idempotency_key=payload.idempotency_key, require_cashier_shift=True))


@router.post("/deposits/{account_id}/forfeit")
def forfeit_deposit_endpoint(account_id: int, payload: DepositForfeitIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.void_transaction", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "deposit_forfeit")
    return _finish(db, lambda: forfeit_deposit(db, property_code=code, account_id=account_id, business_date=payload.business_date, amount=payload.amount, reason=payload.reason, actor=actor["email"], idempotency_key=payload.idempotency_key))


@router.post("/payments/receipt")
def record_payment_receipt(payload: PaymentReceiptIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.post_payment", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "payment_receipt")
    allocations = [item.model_dump() for item in payload.allocations]
    return _finish(db, lambda: receive_split_payment(db, property_code=code, booking_id=payload.booking_id, business_date=payload.business_date, requested_amount=payload.requested_amount, currency=payload.currency.upper(), allocations=allocations, reference=payload.reference, actor=actor["email"], idempotency_key=payload.idempotency_key, require_cashier_shift=True))


@router.post("/payments/refund")
def refund_payment_endpoint(payload: PaymentRefundIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.void_transaction", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "payment_refund")
    return _finish(db, lambda: refund_payment(db, property_code=code, original_transaction_id=payload.original_transaction_id, business_date=payload.business_date, amount=payload.amount, payment_method=payload.payment_method, reason=payload.reason, actor=actor["email"], idempotency_key=payload.idempotency_key, require_cashier_shift=True))


@router.post("/payments/void")
def void_payment_endpoint(payload: PaymentVoidIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.void_transaction", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "payment_void")
    return _finish(db, lambda: void_payment(db, property_code=code, original_transaction_id=payload.original_transaction_id, business_date=payload.business_date, reason=payload.reason, approved_by=payload.approved_by, actor=actor["email"], idempotency_key=payload.idempotency_key, require_cashier_shift=True))
