from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.business_date_lock_service import assert_business_date_editable
from guzo_backend.services.cashier_shift_service import (
    approve_variance,
    close_shift,
    current_shift,
    declare_totals,
    get_shift,
    open_shift,
    request_variance_approval,
    shift_snapshot,
)
from guzo_backend.services.pms_security_service import require_pms_permission, require_property_access


router = APIRouter(prefix="/finance/cashier", tags=["Cashier Shift Control"])


class ShiftOpenIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    cashier_name: str = Field(..., min_length=1)
    assigned_user_email: str | None = None
    opening_float: Decimal = Field(Decimal("0"), ge=0)
    currency: str = Field("ETB", min_length=1)
    notes: str | None = None


class ShiftTotalsIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    cash: Decimal = Field(Decimal("0"), ge=0)
    card: Decimal = Field(Decimal("0"), ge=0)
    bank_transfer: Decimal = Field(Decimal("0"), ge=0)
    mobile_money: Decimal = Field(Decimal("0"), ge=0)
    unassigned: Decimal = Field(Decimal("0"), ge=0)


class ShiftReasonIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    reason: str = Field(..., min_length=3)


class ShiftCloseIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    notes: str | None = None


def _code(value: str) -> str:
    return value.strip().upper()


def _editable(db: Session, code: str, day: date, action: str) -> None:
    assert_business_date_editable(db, property_code=code, business_date=day, module="finance", action=action)


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
        raise HTTPException(status_code=500, detail=f"Cashier shift operation failed: {exc}")


@router.post("/shifts/open")
def open_cashier_shift(payload: ShiftOpenIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.post_payment", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "open_cashier_shift")
    assigned = (payload.assigned_user_email or actor["email"]).strip().lower()
    return _finish(db, lambda: open_shift(db, property_code=code, business_date=payload.business_date, cashier_name=payload.cashier_name, assigned_user_email=assigned, opening_float=payload.opening_float, currency=payload.currency, actor=actor["email"], notes=payload.notes))


@router.get("/shifts/current")
def get_current_cashier_shift(property_code: str = Query(...), business_date: date = Query(...), db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(property_code)
    actor = require_property_access(db, property_code=code, user_email=x_pms_user_email)
    shift = current_shift(db, property_code=code, business_date=business_date, user_email=actor["email"])
    return {"shift": shift}


@router.post("/shifts/{shift_id}/declare")
def declare_cashier_totals(shift_id: int, payload: ShiftTotalsIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.close_cashier", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "declare_cashier_totals")
    return _finish(db, lambda: declare_totals(db, property_code=code, shift_id=shift_id, declared={"cash": payload.cash, "card": payload.card, "bank_transfer": payload.bank_transfer, "mobile_money": payload.mobile_money, "unassigned": payload.unassigned}, actor=actor["email"]))


@router.post("/shifts/{shift_id}/request-approval")
def request_cashier_approval(shift_id: int, payload: ShiftReasonIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.close_cashier", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "request_cashier_variance_approval")
    return _finish(db, lambda: request_variance_approval(db, property_code=code, shift_id=shift_id, reason=payload.reason, actor=actor["email"]))


@router.post("/shifts/{shift_id}/approve")
def approve_cashier_variance(shift_id: int, payload: ShiftReasonIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.approve_variance", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "approve_cashier_variance")
    return _finish(db, lambda: approve_variance(db, property_code=code, shift_id=shift_id, reason=payload.reason, actor=actor["email"]))


@router.post("/shifts/{shift_id}/close")
def close_cashier_shift(shift_id: int, payload: ShiftCloseIn, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(payload.property_code)
    actor = require_pms_permission(db, permission_key="finance.close_cashier", property_code=code, user_email=x_pms_user_email)
    _editable(db, code, payload.business_date, "close_cashier_shift")
    return _finish(db, lambda: close_shift(db, property_code=code, shift_id=shift_id, actor=actor["email"], notes=payload.notes))


@router.get("/shifts/{shift_id}/report")
def cashier_closure_report(shift_id: int, property_code: str = Query(...), db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = _code(property_code)
    require_property_access(db, property_code=code, user_email=x_pms_user_email)
    return shift_snapshot(db, get_shift(db, property_code=code, shift_id=shift_id))
