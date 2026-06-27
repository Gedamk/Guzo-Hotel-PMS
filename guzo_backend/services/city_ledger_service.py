from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.cashier_shift_service import require_open_shift
from guzo_backend.services.finance_transaction_service import get_finance_transaction, post_finance_transaction, reverse_finance_transaction
from guzo_backend.services.pms_security_service import record_pms_audit_log


def money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def rowdict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def company(db: Session, property_code: str, account_id: int, lock: bool = False) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = db.execute(text(f"SELECT * FROM ar_company_accounts WHERE id=:id AND property_code=:code{suffix}"), {"id": account_id, "code": property_code}).mappings().first()
    if not row:
        raise HTTPException(404, "City ledger account not found for selected property.")
    return rowdict(row)


def invoice(db: Session, property_code: str, invoice_id: int, lock: bool = False) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = db.execute(text(f"SELECT * FROM ar_invoices WHERE id=:id AND property_code=:code{suffix}"), {"id": invoice_id, "code": property_code}).mappings().first()
    if not row:
        raise HTTPException(404, "AR invoice not found for selected property.")
    return rowdict(row)


def create_company(db: Session, *, property_code: str, data: dict[str, Any], actor: str) -> dict[str, Any]:
    row = db.execute(text("""INSERT INTO ar_company_accounts(property_code,company_name,account_code,billing_contact,email,phone,address,tax_id,credit_limit,status,payment_terms,allow_direct_bill,created_by)
      VALUES(:property_code,:company_name,:account_code,:billing_contact,:email,:phone,:address,:tax_id,:credit_limit,:status,:payment_terms,:allow_direct_bill,:actor) RETURNING *"""), {**data, "property_code": property_code, "account_code": data["account_code"].strip().upper(), "company_name": data["company_name"].strip(), "status": data.get("status", "active").lower(), "credit_limit": money(data.get("credit_limit")), "actor": actor.lower()}).mappings().first()
    result = rowdict(row)
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="ar_company_created", record_type="ar_company_account", record_id=result["id"], new_value={"account_code": result["account_code"], "company_name": result["company_name"], "credit_limit": str(result["credit_limit"]), "allow_direct_bill": result["allow_direct_bill"]})
    return result


def list_companies(db: Session, property_code: str) -> list[dict[str, Any]]:
    return [rowdict(r) for r in db.execute(text("SELECT * FROM ar_company_accounts WHERE property_code=:code ORDER BY company_name"), {"code": property_code}).mappings().all()]


def update_company_controls(db: Session, *, property_code: str, account_id: int, status: str, allow_direct_bill: bool, credit_limit: Decimal, payment_terms: int, actor: str) -> dict[str, Any]:
    previous = company(db, property_code, account_id, lock=True)
    row = db.execute(text("""UPDATE ar_company_accounts SET status=:status,allow_direct_bill=:allow,credit_limit=:limit,payment_terms=:terms,updated_at=NOW()
      WHERE id=:id AND property_code=:code RETURNING *"""), {"status": status, "allow": allow_direct_bill, "limit": money(credit_limit), "terms": payment_terms, "id": account_id, "code": property_code}).mappings().first()
    result = rowdict(row)
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="ar_company_controls_updated", record_type="ar_company_account", record_id=account_id, old_value={"status": previous["status"], "allow_direct_bill": previous["allow_direct_bill"], "credit_limit": str(previous["credit_limit"])}, new_value={"status": status, "allow_direct_bill": allow_direct_bill, "credit_limit": str(money(credit_limit)), "payment_terms": payment_terms})
    return result


def transfer_folio(db: Session, *, property_code: str, booking_id: int, company_account_id: int, business_date: date, tax: Decimal, actor: str, idempotency_key: str, manager_override_reason: str | None) -> dict[str, Any]:
    account = company(db, property_code, company_account_id, lock=True)
    if account["status"] != "active" or not account["allow_direct_bill"]:
        raise HTTPException(409, "Company account is inactive, on hold, closed, or not authorized for direct billing.")
    folio = db.execute(text("""SELECT f.*, b.guest_name, b.booking_status FROM folios f JOIN bookings b ON b.id=f.booking_id AND b.property_code=f.property_code WHERE f.booking_id=:booking AND f.property_code=:code FOR UPDATE OF f"""), {"booking": booking_id, "code": property_code}).mappings().first()
    if not folio:
        raise HTTPException(404, "Folio not found for selected property.")
    subtotal = money(folio["balance"])
    if subtotal <= 0:
        raise HTTPException(409, "Folio has no positive balance to transfer.")
    override = (manager_override_reason or "").strip()
    if str(folio["booking_status"]).lower() not in {"checked_out", "checked-out"} and not override:
        raise HTTPException(409, "Folio transfer requires checkout or manager-approved transfer reason.")
    total = subtotal + money(tax)
    if money(account["credit_limit"]) > 0 and money(account["current_balance"]) + total > money(account["credit_limit"]) and not override:
        raise HTTPException(409, "Direct-bill transfer exceeds the company credit limit and requires manager override.")
    existing = db.execute(text("SELECT * FROM ar_invoices WHERE property_code=:code AND folio_id=:folio"), {"code": property_code, "folio": folio["id"]}).mappings().first()
    if existing:
        return {**rowdict(existing), "replayed": True}
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, folio_id=folio["id"], booking_id=booking_id, account_reference=account["account_code"], transaction_type="transfer", amount=total, currency=folio.get("currency") or "ETB", direction="credit", reference=f"City ledger transfer to {account['account_code']}", source_document_type="ar_folio_transfer", source_document_id=folio["id"], created_by=actor, idempotency_key=idempotency_key, metadata={"company_account_id": company_account_id, "manager_override_reason": override or None})
    number = f"AR-{property_code}-{business_date:%Y%m%d}-{uuid4().hex[:8].upper()}"
    created = db.execute(text("""INSERT INTO ar_invoices(invoice_number,property_code,company_account_id,folio_id,booking_id,guest_reference,issue_date,due_date,subtotal,tax,total,balance_due,status,transfer_transaction_id,override_reason,created_by)
      VALUES(:number,:code,:account,:folio,:booking,:guest,:issue,:due,:subtotal,:tax,:total,:total,'issued',:ledger,:override,:actor) RETURNING *"""), {"number": number, "code": property_code, "account": company_account_id, "folio": folio["id"], "booking": booking_id, "guest": folio.get("guest_name"), "issue": business_date, "due": business_date + timedelta(days=int(account["payment_terms"])), "subtotal": subtotal, "tax": money(tax), "total": total, "ledger": ledger["id"], "override": override or None, "actor": actor}).mappings().first()
    db.execute(text("INSERT INTO ar_invoice_sources(property_code,invoice_id,finance_transaction_id,source_type,amount) VALUES(:code,:invoice,:ledger,'folio_transfer',:amount)"), {"code": property_code, "invoice": created["id"], "ledger": ledger["id"], "amount": total})
    db.execute(text("UPDATE ar_company_accounts SET current_balance=current_balance+:amount,updated_at=NOW() WHERE id=:id AND property_code=:code"), {"amount": total, "id": company_account_id, "code": property_code})
    db.execute(text("UPDATE folios SET status='transferred_to_billing',transferred_to=:account,transfer_reason=:reason,transferred_at=NOW() WHERE id=:folio AND property_code=:code"), {"account": account["account_code"], "reason": override or "Eligible checked-out folio", "folio": folio["id"], "code": property_code})
    db.execute(text("UPDATE bookings SET payment_status='city_ledger' WHERE id=:booking AND property_code=:code"), {"booking": booking_id, "code": property_code})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="folio_transferred_to_city_ledger", record_type="ar_invoice", record_id=created["id"], new_value={"invoice_number": number, "company_account_id": company_account_id, "total": str(total), "ledger_transaction_id": ledger["id"], "override_reason": override or None})
    return {**rowdict(created), "ledger_transaction_id": ledger["id"], "replayed": False}


def list_invoices(db: Session, property_code: str, company_id: int | None = None) -> list[dict[str, Any]]:
    clause = " AND company_account_id=:company" if company_id else ""
    params = {"code": property_code, "company": company_id}
    rows = db.execute(text(f"SELECT * FROM ar_invoices WHERE property_code=:code{clause} ORDER BY issue_date DESC,id DESC"), params).mappings().all()
    return [rowdict(r) for r in rows]


def receive_payment(db: Session, *, property_code: str, company_account_id: int, business_date: date, amount: Decimal, currency: str, method: str, reference: str | None, channel: str, invoice_ids: list[int], actor: str, idempotency_key: str) -> dict[str, Any]:
    account = company(db, property_code, company_account_id, lock=True)
    if account["status"] == "closed":
        raise HTTPException(409, "Closed company accounts cannot receive AR payments.")
    shift = require_open_shift(db, property_code=property_code, business_date=business_date, actor=actor) if channel == "front_desk" else None
    existing = db.execute(text("SELECT * FROM ar_payments WHERE property_code=:code AND idempotency_key=:key"), {"code": property_code, "key": idempotency_key}).mappings().first()
    if existing:
        return {**rowdict(existing), "replayed": True}
    amount = money(amount)
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, account_reference=account["account_code"], transaction_type="payment", amount=amount, currency=currency, direction="credit", payment_method=method, reference=reference, source_document_type="ar_payment", source_document_id=idempotency_key, created_by=actor, idempotency_key=idempotency_key, cashier_session_id=int(shift["id"]) if shift else None)
    payment = db.execute(text("""INSERT INTO ar_payments(property_code,company_account_id,business_date,amount,currency,payment_method,reference,channel,finance_transaction_id,cashier_session_id,idempotency_key,created_by)
      VALUES(:code,:account,:day,:amount,:currency,:method,:reference,:channel,:ledger,:shift,:key,:actor) RETURNING *"""), {"code": property_code, "account": company_account_id, "day": business_date, "amount": amount, "currency": currency, "method": method, "reference": reference, "channel": channel, "ledger": ledger["id"], "shift": shift["id"] if shift else None, "key": idempotency_key, "actor": actor}).mappings().first()
    remaining = amount
    allocated = Decimal("0")
    params: dict[str, Any] = {"code": property_code, "account": company_account_id}
    filter_sql = ""
    if invoice_ids:
        filter_sql = " AND id = ANY(:ids)"
        params["ids"] = invoice_ids
    invoices = db.execute(text(f"SELECT * FROM ar_invoices WHERE property_code=:code AND company_account_id=:account AND balance_due>0 AND status NOT IN ('voided','draft') {filter_sql} ORDER BY due_date,id FOR UPDATE"), params).mappings().all()
    for inv in invoices:
        allocation = min(remaining, money(inv["balance_due"]))
        if allocation <= 0: break
        new_balance = money(inv["balance_due"]) - allocation
        status = "paid" if new_balance == 0 else "partially_paid"
        db.execute(text("UPDATE ar_invoices SET balance_due=:balance,status=:status WHERE id=:id AND property_code=:code"), {"balance": new_balance, "status": status, "id": inv["id"], "code": property_code})
        db.execute(text("INSERT INTO ar_payment_allocations(property_code,payment_id,invoice_id,amount) VALUES(:code,:payment,:invoice,:amount)"), {"code": property_code, "payment": payment["id"], "invoice": inv["id"], "amount": allocation})
        remaining -= allocation; allocated += allocation
    db.execute(text("UPDATE ar_payments SET allocated_amount=:allocated,unapplied_amount=:unapplied WHERE id=:id"), {"allocated": allocated, "unapplied": remaining, "id": payment["id"]})
    db.execute(text("UPDATE ar_company_accounts SET current_balance=current_balance-:amount,updated_at=NOW() WHERE id=:id AND property_code=:code"), {"amount": amount, "id": company_account_id, "code": property_code})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="ar_payment_received", record_type="ar_payment", record_id=payment["id"], new_value={"amount": str(amount), "allocated": str(allocated), "unapplied": str(remaining), "ledger_transaction_id": ledger["id"], "channel": channel})
    return {**rowdict(payment), "allocated_amount": allocated, "unapplied_amount": remaining, "ledger_transaction_id": ledger["id"], "replayed": False}


def adjust_invoice(db: Session, *, property_code: str, invoice_id: int, business_date: date, amount: Decimal, direction: str, reason: str, actor: str, key: str) -> dict[str, Any]:
    inv = invoice(db, property_code, invoice_id, lock=True); amount = money(amount)
    ledger = post_finance_transaction(db, property_code=property_code, business_date=business_date, folio_id=inv.get("folio_id"), booking_id=inv.get("booking_id"), account_reference=f"AR:{inv['company_account_id']}", transaction_type="adjustment", amount=amount, currency="ETB", direction=direction, reference=reason, source_document_type="ar_invoice_adjustment", source_document_id=invoice_id, created_by=actor, idempotency_key=key)
    delta = amount if direction == "debit" else -amount
    new_balance = max(money(inv["balance_due"]) + delta, Decimal("0"))
    db.execute(text("UPDATE ar_invoices SET balance_due=:balance,status=CASE WHEN :balance=0 THEN 'paid' ELSE 'partially_paid' END WHERE id=:id"), {"balance": new_balance, "id": invoice_id})
    db.execute(text("UPDATE ar_company_accounts SET current_balance=current_balance+:delta,updated_at=NOW() WHERE id=:id AND property_code=:code"), {"delta": delta, "id": inv["company_account_id"], "code": property_code})
    db.execute(text("INSERT INTO ar_adjustments(property_code,invoice_id,amount,direction,reason,finance_transaction_id,created_by) VALUES(:code,:invoice,:amount,:direction,:reason,:ledger,:actor)"), {"code": property_code, "invoice": invoice_id, "amount": amount, "direction": direction, "reason": reason, "ledger": ledger["id"], "actor": actor})
    return {"invoice_id": invoice_id, "balance_due": new_balance, "ledger_transaction_id": ledger["id"]}


def void_invoice(db: Session, *, property_code: str, invoice_id: int, business_date: date, reason: str, actor: str, key: str) -> dict[str, Any]:
    inv = invoice(db, property_code, invoice_id, lock=True)
    if inv["status"] == "voided": raise HTTPException(409, "Invoice is already voided.")
    if money(inv["balance_due"]) != money(inv["total"]): raise HTTPException(409, "Paid or partially-paid invoices must be refunded before voiding.")
    reversal = reverse_finance_transaction(db, property_code=property_code, transaction_id=inv["transfer_transaction_id"], business_date=business_date, reversal_type="void", reason=reason, created_by=actor, idempotency_key=key)
    db.execute(text("UPDATE ar_invoices SET status='voided',balance_due=0,voided_at=NOW() WHERE id=:id AND property_code=:code"), {"id": invoice_id, "code": property_code})
    db.execute(text("UPDATE ar_company_accounts SET current_balance=current_balance-:amount,updated_at=NOW() WHERE id=:id AND property_code=:code"), {"amount": inv["total"], "id": inv["company_account_id"], "code": property_code})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="ar_invoice_voided", record_type="ar_invoice", record_id=invoice_id, new_value={"reason": reason, "original_transaction_id": inv["transfer_transaction_id"], "reversal_transaction_id": reversal["id"]})
    return {"invoice_id": invoice_id, "status": "voided", "original_transaction_id": inv["transfer_transaction_id"], "reversal_transaction_id": reversal["id"]}


def aging(db: Session, property_code: str, as_of: date) -> dict[str, Any]:
    rows = db.execute(text("SELECT * FROM ar_invoices WHERE property_code=:code AND balance_due>0 AND status NOT IN ('voided','draft')"), {"code": property_code}).mappings().all()
    buckets = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "90_plus": Decimal("0")}
    for inv in rows:
        days = (as_of - inv["due_date"]).days
        key = "current" if days <= 0 else "1_30" if days <= 30 else "31_60" if days <= 60 else "61_90" if days <= 90 else "90_plus"
        buckets[key] += money(inv["balance_due"])
    return {"property_code": property_code, "as_of": as_of, "buckets": buckets, "total": sum(buckets.values(), Decimal("0")), "open_invoice_count": len(rows)}


def statement(db: Session, property_code: str, company_id: int) -> dict[str, Any]:
    acct = company(db, property_code, company_id)
    invoices = list_invoices(db, property_code, company_id)
    payments = [rowdict(r) for r in db.execute(text("SELECT * FROM ar_payments WHERE property_code=:code AND company_account_id=:id ORDER BY business_date,id"), {"code": property_code, "id": company_id}).mappings().all()]
    return {"company": acct, "invoices": invoices, "payments": payments}


def statement_csv(data: dict[str, Any]) -> str:
    stream = io.StringIO(); writer = csv.writer(stream)
    writer.writerow(["Company", data["company"]["company_name"], "Account", data["company"]["account_code"]])
    writer.writerow(["Invoice", "Issue Date", "Due Date", "Total", "Balance", "Status"])
    for item in data["invoices"]: writer.writerow([item["invoice_number"], item["issue_date"], item["due_date"], item["total"], item["balance_due"], item["status"]])
    writer.writerow([]); writer.writerow(["Payment Date", "Method", "Amount", "Allocated", "Unapplied", "Reference"])
    for item in data["payments"]: writer.writerow([item["business_date"], item["payment_method"], item["amount"], item["allocated_amount"], item["unapplied_amount"], item["reference"]])
    return stream.getvalue()
