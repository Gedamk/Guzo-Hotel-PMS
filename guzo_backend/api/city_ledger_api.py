from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.business_date_lock_service import assert_business_date_editable
from guzo_backend.services.city_ledger_service import (
    adjust_invoice, aging, create_company, list_companies, list_invoices, receive_payment,
    statement, statement_csv, transfer_folio, update_company_controls, void_invoice,
)
from guzo_backend.services.pms_security_service import require_pms_permission, require_property_access

router = APIRouter(prefix="/finance/ar", tags=["City Ledger / AR"])

class CompanyIn(BaseModel):
    property_code: str; company_name: str = Field(..., min_length=2); account_code: str = Field(..., min_length=2)
    billing_contact: str | None = None; email: EmailStr | None = None; phone: str | None = None
    address: str | None = None; tax_id: str | None = None; credit_limit: Decimal = Field(0, ge=0)
    status: str = Field("active", pattern="^(active|on_hold|closed)$"); payment_terms: int = Field(30, ge=0)
    allow_direct_bill: bool = True

class TransferIn(BaseModel):
    property_code: str; booking_id: int; company_account_id: int; business_date: date
    tax: Decimal = Field(0, ge=0); manager_override_reason: str | None = None; idempotency_key: str = Field(..., min_length=3)

class CompanyControlsIn(BaseModel):
    property_code: str; status: str = Field(..., pattern="^(active|on_hold|closed)$")
    allow_direct_bill: bool; credit_limit: Decimal = Field(..., ge=0); payment_terms: int = Field(..., ge=0)

class PaymentIn(BaseModel):
    property_code: str; company_account_id: int; business_date: date; amount: Decimal = Field(..., gt=0)
    currency: str = "ETB"; payment_method: str = Field(..., min_length=1); reference: str | None = None
    channel: str = Field("back_office", pattern="^(front_desk|back_office)$"); invoice_ids: list[int] = Field(default_factory=list)
    idempotency_key: str = Field(..., min_length=3)

class AdjustmentIn(BaseModel):
    property_code: str; business_date: date; amount: Decimal = Field(..., gt=0)
    direction: str = Field(..., pattern="^(debit|credit)$"); reason: str = Field(..., min_length=3); idempotency_key: str

class VoidIn(BaseModel):
    property_code: str; business_date: date; reason: str = Field(..., min_length=3); idempotency_key: str

def code(value: str) -> str: return value.strip().upper()
def editable(db: Session, property_code: str, day: date, action: str):
    assert_business_date_editable(db, property_code=property_code, business_date=day, module="finance", action=action)
def finish(db: Session, operation):
    try:
        result = operation(); db.commit(); return result
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(500, f"City ledger operation failed: {exc}")

@router.post("/companies")
def create_company_account(payload: CompanyIn, db: Session=Depends(get_db), x_pms_user_email: str|None=Header(None)):
    property_code=code(payload.property_code); actor=require_pms_permission(db,permission_key="finance.transfer_balance",property_code=property_code,user_email=x_pms_user_email)
    return finish(db,lambda:create_company(db,property_code=property_code,data=payload.model_dump(exclude={"property_code"}),actor=actor["email"]))

@router.get("/companies")
def get_companies(property_code: str=Query(...), db: Session=Depends(get_db), x_pms_user_email: str|None=Header(None)):
    property_code=code(property_code); require_property_access(db,property_code=property_code,user_email=x_pms_user_email); return list_companies(db,property_code)

@router.put("/companies/{account_id}/controls")
def set_company_controls(account_id:int,payload:CompanyControlsIn,db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(payload.property_code);actor=require_pms_permission(db,permission_key="finance.transfer_balance",property_code=property_code,user_email=x_pms_user_email)
    return finish(db,lambda:update_company_controls(db,property_code=property_code,account_id=account_id,status=payload.status,allow_direct_bill=payload.allow_direct_bill,credit_limit=payload.credit_limit,payment_terms=payload.payment_terms,actor=actor["email"]))

@router.post("/transfers")
def create_transfer(payload: TransferIn, db: Session=Depends(get_db), x_pms_user_email: str|None=Header(None)):
    property_code=code(payload.property_code); actor=require_pms_permission(db,permission_key="finance.transfer_balance",property_code=property_code,user_email=x_pms_user_email); editable(db,property_code,payload.business_date,"city_ledger_transfer")
    return finish(db,lambda:transfer_folio(db,property_code=property_code,booking_id=payload.booking_id,company_account_id=payload.company_account_id,business_date=payload.business_date,tax=payload.tax,actor=actor["email"],idempotency_key=payload.idempotency_key,manager_override_reason=payload.manager_override_reason))

@router.get("/invoices")
def get_invoices(property_code: str=Query(...), company_account_id: int|None=Query(None), db: Session=Depends(get_db), x_pms_user_email: str|None=Header(None)):
    property_code=code(property_code); require_property_access(db,property_code=property_code,user_email=x_pms_user_email); return list_invoices(db,property_code,company_account_id)

@router.post("/payments")
def create_ar_payment(payload: PaymentIn, db: Session=Depends(get_db), x_pms_user_email: str|None=Header(None)):
    property_code=code(payload.property_code); permission="finance.post_payment" if payload.channel=="front_desk" else "finance.transfer_balance"
    actor=require_pms_permission(db,permission_key=permission,property_code=property_code,user_email=x_pms_user_email); editable(db,property_code,payload.business_date,"ar_payment")
    return finish(db,lambda:receive_payment(db,property_code=property_code,company_account_id=payload.company_account_id,business_date=payload.business_date,amount=payload.amount,currency=payload.currency.upper(),method=payload.payment_method.lower(),reference=payload.reference,channel=payload.channel,invoice_ids=payload.invoice_ids,actor=actor["email"],idempotency_key=payload.idempotency_key))

@router.post("/invoices/{invoice_id}/adjust")
def create_adjustment(invoice_id:int,payload:AdjustmentIn,db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(payload.property_code); actor=require_pms_permission(db,permission_key="finance.void_transaction",property_code=property_code,user_email=x_pms_user_email); editable(db,property_code,payload.business_date,"ar_adjustment")
    return finish(db,lambda:adjust_invoice(db,property_code=property_code,invoice_id=invoice_id,business_date=payload.business_date,amount=payload.amount,direction=payload.direction,reason=payload.reason,actor=actor["email"],key=payload.idempotency_key))

@router.post("/invoices/{invoice_id}/void")
def void_ar_invoice(invoice_id:int,payload:VoidIn,db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(payload.property_code); actor=require_pms_permission(db,permission_key="finance.void_transaction",property_code=property_code,user_email=x_pms_user_email); editable(db,property_code,payload.business_date,"ar_invoice_void")
    return finish(db,lambda:void_invoice(db,property_code=property_code,invoice_id=invoice_id,business_date=payload.business_date,reason=payload.reason,actor=actor["email"],key=payload.idempotency_key))

@router.get("/aging")
def get_aging(property_code:str=Query(...),as_of:date=Query(...),db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(property_code);require_property_access(db,property_code=property_code,user_email=x_pms_user_email);return aging(db,property_code,as_of)

@router.get("/companies/{company_id}/statement")
def get_statement(company_id:int,property_code:str=Query(...),db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(property_code);require_property_access(db,property_code=property_code,user_email=x_pms_user_email);return statement(db,property_code,company_id)

@router.get("/companies/{company_id}/statement.csv")
def export_statement(company_id:int,property_code:str=Query(...),db:Session=Depends(get_db),x_pms_user_email:str|None=Header(None)):
    property_code=code(property_code);require_property_access(db,property_code=property_code,user_email=x_pms_user_email);content=statement_csv(statement(db,property_code,company_id));return Response(content,media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{property_code}-ar-statement-{company_id}.csv"'})
