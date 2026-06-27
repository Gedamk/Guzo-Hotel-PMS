from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guzo_backend.services.pms_security_service import record_pms_audit_log


METHODS = ("cash", "card", "bank_transfer", "mobile_money", "unassigned")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _method(value: str | None) -> str:
    key = (value or "").strip().lower()
    if key in {"pos", "credit_card", "debit_card"}:
        return "card"
    if key in {"bank", "wire"}:
        return "bank_transfer"
    if key in {"telebirr", "cbebirr", "mobile"}:
        return "mobile_money"
    return key if key in METHODS else "unassigned"


def get_shift(db: Session, *, property_code: str, shift_id: int, lock: bool = False) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = db.execute(text(f"SELECT * FROM cashier_sessions WHERE id=:id AND property_code=:code{suffix}"), {"id": shift_id, "code": property_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Cashier shift not found for selected property.")
    return _dict(row)


def current_shift(db: Session, *, property_code: str, business_date: date, user_email: str | None = None) -> dict[str, Any] | None:
    clauses = ["property_code=:code", "business_date=:day", "status <> 'closed'"]
    params: dict[str, Any] = {"code": property_code, "day": business_date}
    if user_email:
        clauses.append("assigned_user_email=:email")
        params["email"] = user_email.strip().lower()
    row = db.execute(text(f"SELECT * FROM cashier_sessions WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT 1"), params).mappings().first()
    return shift_snapshot(db, _dict(row)) if row else None


def expected_totals(db: Session, *, shift_id: int, opening_float: Decimal = Decimal("0")) -> dict[str, Decimal]:
    rows = db.execute(
        text("""
            SELECT payment_method, direction, amount
            FROM finance_transactions
            WHERE cashier_session_id=:shift_id
              AND transaction_type IN ('payment','deposit','refund','void')
        """), {"shift_id": shift_id}
    ).mappings().all()
    totals = {key: Decimal("0.00") for key in METHODS}
    totals["cash"] += _money(opening_float)
    for row in rows:
        amount = _money(row["amount"])
        totals[_method(row.get("payment_method"))] += amount if row["direction"] == "credit" else -amount
    return totals


def shift_snapshot(db: Session, shift: dict[str, Any]) -> dict[str, Any]:
    if not shift:
        return {}
    totals = expected_totals(db, shift_id=int(shift["id"]), opening_float=_money(shift.get("opening_float")))
    declared = {key: _money(shift.get(f"actual_{key}")) for key in METHODS}
    return {
        **shift,
        "expected_by_method": totals,
        "declared_by_method": declared,
        "expected_total": sum(totals.values(), Decimal("0")),
        "declared_total": sum(declared.values(), Decimal("0")),
        "variance": sum(declared.values(), Decimal("0")) - sum(totals.values(), Decimal("0")),
    }


def open_shift(db: Session, *, property_code: str, business_date: date, cashier_name: str, assigned_user_email: str, opening_float: Decimal, currency: str, actor: str, notes: str | None) -> dict[str, Any]:
    try:
        row = db.execute(text("""
            INSERT INTO cashier_sessions(property_code,business_date,cashier_name,assigned_user_email,opened_by,opening_float,currency,status,notes,opened_at,closed_at)
            VALUES(:code,:day,:name,:assigned,:actor,:float,:currency,'open',:notes,NOW(),NULL)
            RETURNING *
        """), {"code": property_code, "day": business_date, "name": cashier_name.strip(), "assigned": assigned_user_email.strip().lower(), "actor": actor.lower(), "float": _money(opening_float), "currency": currency.upper(), "notes": notes}).mappings().first()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="This cashier already has an active shift for the selected property and business date.")
    result = _dict(row)
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_shift_opened", record_type="cashier_session", record_id=result["id"], new_value={"business_date": str(business_date), "assigned_user_email": assigned_user_email, "opening_float": str(_money(opening_float))})
    return shift_snapshot(db, result)


def require_open_shift(db: Session, *, property_code: str, business_date: date, actor: str, manager_override_reason: str | None = None) -> dict[str, Any] | None:
    row = db.execute(text("""
        SELECT * FROM cashier_sessions
        WHERE property_code=:code AND business_date=:day
          AND assigned_user_email=:actor AND status='open'
        ORDER BY id DESC LIMIT 1 FOR UPDATE
    """), {"code": property_code, "day": business_date, "actor": actor.strip().lower()}).mappings().first()
    if row:
        return _dict(row)
    if manager_override_reason and manager_override_reason.strip():
        record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_shift_override", record_type="cashier_session", record_id=None, new_value={"business_date": str(business_date), "reason": manager_override_reason.strip()})
        return None
    raise HTTPException(status_code=409, detail="An open cashier shift assigned to the current user is required for this transaction.")


def declare_totals(db: Session, *, property_code: str, shift_id: int, declared: dict[str, Decimal], actor: str) -> dict[str, Any]:
    shift = get_shift(db, property_code=property_code, shift_id=shift_id, lock=True)
    if shift["status"] != "open":
        raise HTTPException(status_code=409, detail="Only an open cashier shift can accept declared totals.")
    values = {key: _money(declared.get(key, 0)) for key in METHODS}
    expected = expected_totals(db, shift_id=shift_id, opening_float=_money(shift.get("opening_float")))
    variance = sum(values.values(), Decimal("0")) - sum(expected.values(), Decimal("0"))
    status = "declared" if abs(variance) < Decimal("0.01") else "approval_required"
    db.execute(text("""
        UPDATE cashier_sessions SET actual_cash=:cash,actual_card=:card,actual_bank_transfer=:bank_transfer,
          actual_mobile_money=:mobile_money,actual_unassigned=:unassigned,expected_total=:expected,
          declared_total=:declared,variance=:variance,status=:status,declared_at=NOW()
        WHERE id=:id AND property_code=:code
    """), {**values, "expected": sum(expected.values(), Decimal("0")), "declared": sum(values.values(), Decimal("0")), "variance": variance, "status": status, "id": shift_id, "code": property_code})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_totals_declared", record_type="cashier_session", record_id=shift_id, new_value={"declared": {k: str(v) for k, v in values.items()}, "expected": {k: str(v) for k, v in expected.items()}, "variance": str(variance), "status": status})
    return shift_snapshot(db, get_shift(db, property_code=property_code, shift_id=shift_id))


def request_variance_approval(db: Session, *, property_code: str, shift_id: int, reason: str, actor: str) -> dict[str, Any]:
    shift = get_shift(db, property_code=property_code, shift_id=shift_id, lock=True)
    if shift["status"] != "approval_required":
        raise HTTPException(status_code=409, detail="This shift does not have an unapproved variance.")
    db.execute(text("UPDATE cashier_sessions SET status='approval_requested',manager_approval_reason=:reason,approval_requested_at=NOW() WHERE id=:id"), {"reason": reason.strip(), "id": shift_id})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_variance_approval_requested", record_type="cashier_session", record_id=shift_id, new_value={"reason": reason.strip(), "variance": str(shift.get("variance"))})
    return shift_snapshot(db, get_shift(db, property_code=property_code, shift_id=shift_id))


def approve_variance(db: Session, *, property_code: str, shift_id: int, reason: str, actor: str) -> dict[str, Any]:
    shift = get_shift(db, property_code=property_code, shift_id=shift_id, lock=True)
    if shift["status"] not in {"approval_required", "approval_requested"}:
        raise HTTPException(status_code=409, detail="This shift is not awaiting variance approval.")
    db.execute(text("UPDATE cashier_sessions SET status='approved',manager_approved_by=:actor,manager_approval_reason=:reason,approved_at=NOW() WHERE id=:id"), {"actor": actor.lower(), "reason": reason.strip(), "id": shift_id})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_variance_approved", record_type="cashier_session", record_id=shift_id, new_value={"reason": reason.strip(), "variance": str(shift.get("variance"))})
    return shift_snapshot(db, get_shift(db, property_code=property_code, shift_id=shift_id))


def close_shift(db: Session, *, property_code: str, shift_id: int, actor: str, notes: str | None = None) -> dict[str, Any]:
    shift = get_shift(db, property_code=property_code, shift_id=shift_id, lock=True)
    if shift["status"] == "closed":
        raise HTTPException(status_code=409, detail="Cashier shift is already closed.")
    snapshot = shift_snapshot(db, shift)
    variance = _money(snapshot["variance"])
    if not shift.get("declared_at"):
        raise HTTPException(status_code=409, detail="Declare cashier totals before closing the shift.")
    if abs(variance) >= Decimal("0.01") and not shift.get("manager_approved_by"):
        raise HTTPException(status_code=409, detail="Cashier variance requires manager approval before close.")
    report = {"expected_by_method": {k: str(v) for k, v in snapshot["expected_by_method"].items()}, "declared_by_method": {k: str(v) for k, v in snapshot["declared_by_method"].items()}, "expected_total": str(snapshot["expected_total"]), "declared_total": str(snapshot["declared_total"]), "variance": str(variance)}
    db.execute(text("""
        UPDATE cashier_sessions SET status='closed',closed_at=NOW(),closed_by=:actor,notes=COALESCE(:notes,notes),
          cash=:cash,card=:card,bank_transfer=:bank_transfer,mobile_money=:mobile_money,unassigned=:unassigned,
          expected_total=:expected,declared_total=:declared,variance=:variance,closure_report=CAST(:report AS JSONB)
        WHERE id=:id AND property_code=:code
    """), {"actor": actor.lower(), "notes": notes, **snapshot["expected_by_method"], "expected": snapshot["expected_total"], "declared": snapshot["declared_total"], "variance": variance, "report": json.dumps(report), "id": shift_id, "code": property_code})
    record_pms_audit_log(db, property_code=property_code, user_email=actor, module="finance", action="cashier_shift_closed", record_type="cashier_session", record_id=shift_id, new_value=report)
    return shift_snapshot(db, get_shift(db, property_code=property_code, shift_id=shift_id))
