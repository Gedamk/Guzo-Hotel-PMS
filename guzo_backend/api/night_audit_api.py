from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.api.finance_api import get_finance_control_report
from guzo_backend.services.rate_quote_service import quote_stay
from guzo_backend.services.business_date_lock_service import (
    ensure_business_date_lock_table,
    lock_business_date,
    reopen_business_date,
)
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission

router = APIRouter(prefix="/night-audit", tags=["night-audit"])


class NightAuditRunRequest(BaseModel):
    property_code: str
    business_date: Optional[date] = None
    run_by: Optional[str] = None
    notes: Optional[str] = None


class NightAuditOverrideRequest(BaseModel):
    property_code: str
    business_date: date
    exception_key: str
    override_by: Optional[str] = None
    override_reason: Optional[str] = None


class BusinessDateOverrideRequest(BaseModel):
    property_code: str
    business_date: date
    reason: Optional[str] = None


def _next_day(value: date) -> date:
    return value + timedelta(days=1)


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


def _as_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _ensure_night_audit_posting_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS folio_transactions (
                id SERIAL PRIMARY KEY,
                folio_id INTEGER NOT NULL,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                txn_type VARCHAR(50) NOT NULL,
                category VARCHAR(80) NOT NULL,
                description TEXT,
                amount NUMERIC(12, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'ETB',
                booking_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS night_audit_postings (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                booking_id INTEGER NOT NULL,
                folio_id INTEGER,
                posting_type VARCHAR(80) NOT NULL,
                folio_transaction_id INTEGER,
                amount NUMERIC(12, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'ETB',
                status VARCHAR(50) DEFAULT 'posted',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE(property_code, business_date, booking_id, posting_type)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS business_date_locks (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                status VARCHAR(50) DEFAULT 'locked',
                locked_by VARCHAR(150),
                locked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                closed_by VARCHAR(150),
                closed_at TIMESTAMPTZ,
                reopened_by VARCHAR(150),
                reopened_at TIMESTAMPTZ,
                notes TEXT,
                UNIQUE(property_code, business_date)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS report_archive (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                report_key VARCHAR(120) NOT NULL,
                report_name VARCHAR(200) NOT NULL,
                report_payload JSONB,
                status VARCHAR(50) DEFAULT 'generated',
                generated_by VARCHAR(100),
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _get_or_create_folio(db: Session, property_code: str, booking_id: int, guest_name: str, currency: str = "ETB") -> int:
    row = db.execute(
        text(
            """
            SELECT id
            FROM folios
            WHERE property_code = :property_code
              AND booking_id = :booking_id
              AND COALESCE(status, 'open') = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).first()
    if row:
        return int(row[0])

    created = db.execute(
        text(
            """
            INSERT INTO folios (
                property_code, booking_id, guest_name, currency, status,
                total_charges, total_payments, balance
            )
            VALUES (
                :property_code, :booking_id, :guest_name, :currency, 'open',
                0, 0, 0
            )
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "booking_id": booking_id,
            "guest_name": guest_name or "Guest",
            "currency": currency,
        },
    ).first()
    return int(created[0])


def _refresh_folio_totals(db: Session, folio_id: int) -> None:
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
    db.execute(
        text(
            """
            UPDATE folios
            SET total_charges = :total_charges,
                total_payments = :total_payments,
                balance = :balance
            WHERE id = :folio_id
            """
        ),
        {
            "folio_id": folio_id,
            "total_charges": total_charges,
            "total_payments": total_payments,
            "balance": total_charges - total_payments,
        },
    )


def _post_folio_charge_once(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    booking_id: int,
    folio_id: int,
    posting_type: str,
    category: str,
    description: str,
    amount: Decimal,
    currency: str,
) -> dict:
    existing = db.execute(
        text(
            """
            SELECT id, folio_transaction_id, amount
            FROM night_audit_postings
            WHERE property_code = :property_code
              AND business_date = :business_date
              AND booking_id = :booking_id
              AND posting_type = :posting_type
            LIMIT 1
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "booking_id": booking_id,
            "posting_type": posting_type,
        },
    ).mappings().first()
    if existing:
        return {
            "posted": False,
            "duplicate": True,
            "posting_type": posting_type,
            "folio_transaction_id": existing["folio_transaction_id"],
            "amount": float(existing["amount"] or 0),
        }

    txn = db.execute(
        text(
            """
            INSERT INTO folio_transactions (
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
            VALUES (
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
            "business_date": business_date,
            "category": category,
            "description": description,
            "amount": amount,
            "currency": currency,
            "booking_id": booking_id,
        },
    ).first()
    db.execute(
        text(
            """
            INSERT INTO night_audit_postings (
                property_code,
                business_date,
                booking_id,
                folio_id,
                posting_type,
                folio_transaction_id,
                amount,
                currency,
                status
            )
            VALUES (
                :property_code,
                :business_date,
                :booking_id,
                :folio_id,
                :posting_type,
                :folio_transaction_id,
                :amount,
                :currency,
                'posted'
            )
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "booking_id": booking_id,
            "folio_id": folio_id,
            "posting_type": posting_type,
            "folio_transaction_id": int(txn[0]),
            "amount": amount,
            "currency": currency,
        },
    )
    return {
        "posted": True,
        "duplicate": False,
        "posting_type": posting_type,
        "folio_transaction_id": int(txn[0]),
        "amount": float(amount),
    }


def _booking_amount_expression(columns: set[str]) -> str:
    candidates = [
        column
        for column in ["rate_per_night_etb", "total_revenue_etb", "total_amount_etb", "total_amount"]
        if column in columns
    ]
    if not candidates:
        return "0"
    return f"COALESCE({', '.join(candidates)}, 0)"


def _nightly_rate_for_booking(db: Session, booking: dict, business_date: date) -> Decimal:
    stored = _as_decimal(booking.get("nightly_rate"))
    if stored > 0:
        return stored

    quote = quote_stay(
        property_code=booking["property_code"],
        check_in=business_date,
        check_out=business_date + timedelta(days=1),
        room_type=booking.get("room_type"),
        rooms=1,
        adults=1,
        children=0,
        rate_code="BAR",
        db=db,
    )
    return _as_decimal(quote["nightly_rate_etb"])


def _charge_percentages_for_booking(db: Session, booking: dict, business_date: date) -> tuple[Decimal, Decimal]:
    quote = quote_stay(
        property_code=booking["property_code"],
        check_in=business_date,
        check_out=business_date + timedelta(days=1),
        room_type=booking.get("room_type"),
        rooms=1,
        adults=1,
        children=0,
        rate_code="BAR",
        db=db,
    )
    return _as_decimal(quote["service_charge_percent"]), _as_decimal(quote["tax_percent"])


def _post_nightly_charges(db: Session, property_code: str, business_date: date) -> dict:
    _ensure_night_audit_posting_tables(db)
    booking_columns = _table_columns(db, "bookings")
    rate_expr = _booking_amount_expression(booking_columns)
    currency_expr = "COALESCE(currency, 'ETB')" if "currency" in booking_columns else "'ETB'"
    rows = db.execute(
        text(
            f"""
            SELECT
              id,
              property_code,
              guest_name,
              room_type,
              {rate_expr} AS nightly_rate,
              {currency_expr} AS currency
            FROM bookings
            WHERE property_code = :property_code
              AND LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
              AND check_in_date <= :business_date
              AND check_out_date > :business_date
            ORDER BY id
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().all()

    results: list[dict] = []
    for row in rows:
        booking = dict(row)
        booking_id = int(booking["id"])
        currency = booking.get("currency") or "ETB"
        folio_id = _get_or_create_folio(db, property_code, booking_id, booking.get("guest_name") or "Guest", currency)
        room_charge = _nightly_rate_for_booking(db, booking, business_date)
        service_percent, tax_percent = _charge_percentages_for_booking(db, booking, business_date)
        service_charge = (room_charge * service_percent).quantize(Decimal("0.01"))
        tax_charge = ((room_charge + service_charge) * tax_percent).quantize(Decimal("0.01"))
        posted_rows = [
            _post_folio_charge_once(
                db,
                property_code=property_code,
                business_date=business_date,
                booking_id=booking_id,
                folio_id=folio_id,
                posting_type="room_charge",
                category="room",
                description=f"Night Audit room charge for {business_date.isoformat()}",
                amount=room_charge,
                currency=currency,
            ),
            _post_folio_charge_once(
                db,
                property_code=property_code,
                business_date=business_date,
                booking_id=booking_id,
                folio_id=folio_id,
                posting_type="service_charge",
                category="service_charge",
                description=f"Night Audit service charge for {business_date.isoformat()}",
                amount=service_charge,
                currency=currency,
            ),
            _post_folio_charge_once(
                db,
                property_code=property_code,
                business_date=business_date,
                booking_id=booking_id,
                folio_id=folio_id,
                posting_type="tax",
                category="tax",
                description=f"Night Audit tax charge for {business_date.isoformat()}",
                amount=tax_charge,
                currency=currency,
            ),
        ]
        _refresh_folio_totals(db, folio_id)
        results.append(
            {
                "booking_id": booking_id,
                "folio_id": folio_id,
                "room_charge": float(room_charge),
                "service_charge": float(service_charge),
                "tax": float(tax_charge),
                "posted": sum(1 for item in posted_rows if item["posted"]),
                "duplicates": sum(1 for item in posted_rows if item["duplicate"]),
            }
        )

    return {
        "in_house_bookings": len(rows),
        "posted_transactions": sum(row["posted"] for row in results),
        "duplicate_transactions": sum(row["duplicates"] for row in results),
        "rows": results,
    }


def _process_no_show_candidates(db: Session, property_code: str, business_date: date) -> dict:
    _ensure_night_audit_posting_tables(db)
    booking_columns = _table_columns(db, "bookings")
    rate_expr = _booking_amount_expression(booking_columns)
    currency_expr = "COALESCE(currency, 'ETB')" if "currency" in booking_columns else "'ETB'"
    rows = db.execute(
        text(
            f"""
            SELECT
              id,
              property_code,
              guest_name,
              room_type,
              {rate_expr} AS nightly_rate,
              {currency_expr} AS currency
            FROM bookings
            WHERE property_code = :property_code
              AND check_in_date = :business_date
              AND LOWER(COALESCE(booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'pending')
            ORDER BY id
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().all()
    results: list[dict] = []
    for row in rows:
        booking = dict(row)
        booking_id = int(booking["id"])
        currency = booking.get("currency") or "ETB"
        folio_id = _get_or_create_folio(db, property_code, booking_id, booking.get("guest_name") or "Guest", currency)
        no_show_charge = _nightly_rate_for_booking(db, booking, business_date)
        posted = _post_folio_charge_once(
            db,
            property_code=property_code,
            business_date=business_date,
            booking_id=booking_id,
            folio_id=folio_id,
            posting_type="no_show_charge",
            category="no_show",
            description=f"Night Audit no-show charge for {business_date.isoformat()}",
            amount=no_show_charge,
            currency=currency,
        )
        _refresh_folio_totals(db, folio_id)
        db.execute(
            text(
                """
                UPDATE bookings
                SET booking_status = 'no_show'
                WHERE id = :booking_id
                  AND property_code = :property_code
                """
            ),
            {"booking_id": booking_id, "property_code": property_code},
        )
        results.append(
            {
                "booking_id": booking_id,
                "folio_id": folio_id,
                "no_show_charge": float(no_show_charge),
                "posted": posted["posted"],
                "duplicate": posted["duplicate"],
            }
        )
    return {
        "no_show_candidates": len(rows),
        "marked_no_show": len(rows),
        "posted_transactions": sum(1 for row in results if row["posted"]),
        "duplicate_transactions": sum(1 for row in results if row["duplicate"]),
        "rows": results,
    }


def _lock_business_date(db: Session, property_code: str, business_date: date, locked_by: str | None, notes: str | None) -> None:
    lock_business_date(
        db,
        property_code=property_code,
        business_date=business_date,
        closed_by=locked_by,
        notes=notes,
    )


def _archive_night_audit_report(db: Session, property_code: str, business_date: date, run_by: str | None, payload: dict) -> int:
    _ensure_night_audit_posting_tables(db)
    import json

    created = db.execute(
        text(
            """
            INSERT INTO report_archive (
                property_code,
                business_date,
                report_key,
                report_name,
                report_payload,
                status,
                generated_by
            )
            VALUES (
                :property_code,
                :business_date,
                'night_audit_close',
                'Night Audit Close Package',
                CAST(:report_payload AS JSONB),
                'generated',
                :generated_by
            )
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "report_payload": json.dumps(payload, default=str),
            "generated_by": run_by,
        },
    ).first()
    return int(created[0])


def _night_audit_report_package(db: Session, property_code: str, business_date: date) -> dict:
    finance_report = get_finance_control_report(property_code=property_code, business_date=business_date, db=db)
    occupancy = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')) AS in_house,
              COUNT(*) FILTER (WHERE check_in_date = :business_date) AS arrivals,
              COUNT(*) FILTER (WHERE check_out_date = :business_date) AS departures,
              COUNT(*) FILTER (WHERE LOWER(COALESCE(booking_status, '')) IN ('no_show', 'no-show')) AS no_shows
            FROM bookings
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    payment_summary = []
    if _table_exists(db, "folio_transactions"):
        payment_summary = [
            dict(row) | {"amount": float(row["amount"] or 0)}
            for row in db.execute(
                text(
                    """
                    SELECT COALESCE(category, payment_method, 'unassigned') AS method,
                           COALESCE(SUM(amount), 0) AS amount,
                           COUNT(*) AS count
                    FROM folio_transactions
                    WHERE property_code = :property_code
                      AND business_date = :business_date
                      AND txn_type = 'payment'
                    GROUP BY COALESCE(category, payment_method, 'unassigned')
                    ORDER BY method
                    """
                ),
                {"property_code": property_code, "business_date": business_date},
            ).mappings().all()
        ]
    housekeeping_discrepancies = [
        item
        for item in _housekeeping_exceptions(db, property_code)
        if item["exception_key"] in {"dirty_occupied_rooms", "rooms_out_of_order_or_service"}
    ]
    no_show_rows = []
    if _table_exists(db, "bookings"):
        no_show_rows = [
            {
                "booking_id": row["id"],
                "guest_name": row["guest_name"],
                "room_type": row["room_type"],
                "status": row["booking_status"],
            }
            for row in db.execute(
                text(
                    """
                    SELECT id, guest_name, room_type, booking_status
                    FROM bookings
                    WHERE property_code = :property_code
                      AND check_in_date = :business_date
                      AND LOWER(COALESCE(booking_status, '')) IN ('no_show', 'no-show')
                    ORDER BY id
                    """
                ),
                {"property_code": property_code, "business_date": business_date},
            ).mappings().all()
        ]
    return {
        "occupancy_summary": {
            "in_house": int((occupancy or {}).get("in_house") or 0),
            "arrivals": int((occupancy or {}).get("arrivals") or 0),
            "departures": int((occupancy or {}).get("departures") or 0),
            "no_shows": int((occupancy or {}).get("no_shows") or 0),
        },
        "revenue_summary": finance_report.get("daily_revenue") or {},
        "payment_method_summary": payment_summary,
        "cashier_shift_summary": finance_report.get("cashier_shift") or {},
        "open_balance_exception_report": [
            row for row in finance_report.get("guest_ledger") or [] if float(row.get("balance") or 0) != 0
        ],
        "housekeeping_discrepancy_report": housekeeping_discrepancies,
        "no_show_report": no_show_rows,
    }


def _roll_property_business_date(db: Session, property_code: str, next_business_date: date) -> bool:
    rolled = False
    if _table_exists(db, "hotels"):
        columns = _table_columns(db, "hotels")
        for column in ["business_date", "current_business_date"]:
            if column in columns:
                db.execute(
                    text(
                        f"""
                        UPDATE hotels
                        SET {column} = :next_business_date
                        WHERE property_code = :property_code
                        """
                    ),
                    {"property_code": property_code, "next_business_date": next_business_date},
                )
                rolled = True
    return rolled


def _exception(
    *,
    key: str,
    department: str,
    severity: str,
    message: str,
    is_blocking: bool,
    override_allowed: bool = False,
    action: str | None = None,
    count: int | None = None,
    related_booking_id: int | None = None,
    related_folio_id: int | None = None,
    related_room_number: str | None = None,
) -> dict:
    return {
        "exception_key": key,
        "department": department,
        "severity": severity,
        "message": message,
        "is_blocking": is_blocking,
        "override_allowed": override_allowed,
        "resolved": False,
        "action": action,
        "count": count,
        "related_booking_id": related_booking_id,
        "related_folio_id": related_folio_id,
        "related_room_number": related_room_number,
    }


def _status_count(db: Session, property_code: str, business_date: date, status: str) -> int:
    result = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE property_code = :property_code
              AND LOWER(COALESCE(booking_status, '')) = :status
              AND (
                check_in_date = :business_date
                OR check_out_date = :business_date
                OR (:business_date BETWEEN check_in_date AND check_out_date)
              )
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "status": status,
        },
    )
    return int(result.scalar() or 0)


def _movement_snapshot(db: Session, property_code: str, business_date: date) -> dict[str, int]:
    result = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE check_in_date = :business_date) AS arrivals_count,
              COUNT(*) FILTER (WHERE check_out_date = :business_date) AS departures_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
              ) AS in_house_count
            FROM bookings
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()

    return {
        "arrivals_count": int((result or {}).get("arrivals_count") or 0),
        "departures_count": int((result or {}).get("departures_count") or 0),
        "in_house_count": int((result or {}).get("in_house_count") or 0),
        "no_show_count": _status_count(db, property_code, business_date, "no_show"),
    }


def _frontdesk_exceptions(db: Session, property_code: str, business_date: date) -> list[dict]:
    row = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (
                WHERE check_in_date = :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'pending')
              ) AS arrivals_remaining,
              COUNT(*) FILTER (
                WHERE check_in_date = :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'pending')
              ) AS no_show_candidates,
              COUNT(*) FILTER (
                WHERE check_out_date = :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
              ) AS departures_remaining
            FROM bookings
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()

    exceptions: list[dict] = []
    arrivals_remaining = int((row or {}).get("arrivals_remaining") or 0)
    no_show_candidates = int((row or {}).get("no_show_candidates") or 0)
    departures_remaining = int((row or {}).get("departures_remaining") or 0)

    if arrivals_remaining:
        exceptions.append(
            _exception(
                key="frontdesk_expected_arrivals_remaining",
                department="frontdesk",
                severity="critical",
                message=f"{arrivals_remaining} expected arrival(s) still need check-in, no-show, or manager review.",
                is_blocking=True,
                override_allowed=False,
                action="Resolve Front Desk",
                count=arrivals_remaining,
            )
        )
    if no_show_candidates:
        exceptions.append(
            _exception(
                key="no_show_candidates",
                department="frontdesk",
                severity="warning",
                message=f"{no_show_candidates} arrival(s) may need no-show review before audit close.",
                is_blocking=False,
                override_allowed=True,
                action="Mark No-Show",
                count=no_show_candidates,
            )
        )
    if departures_remaining:
        exceptions.append(
            _exception(
                key="frontdesk_departures_remaining",
                department="frontdesk",
                severity="critical",
                message=f"{departures_remaining} due-out in-house guest(s) are not checked out.",
                is_blocking=True,
                override_allowed=False,
                action="Check Out Guest",
                count=departures_remaining,
            )
        )
    return exceptions


def _housekeeping_exceptions(db: Session, property_code: str) -> list[dict]:
    if not _table_exists(db, "bookings") or not _table_exists(db, "rooms"):
        return []

    room_columns = _table_columns(db, "rooms")
    status_expr = "r.status" if "status" in room_columns else "r.housekeeping_status" if "housekeeping_status" in room_columns else "'unknown'"

    mismatch_rows = db.execute(
        text(
            f"""
            SELECT
              b.id AS booking_id,
              b.room_number,
              COALESCE({status_expr}, 'unknown') AS room_status
            FROM bookings b
            LEFT JOIN rooms r
              ON r.property_code = b.property_code
             AND CAST(r.room_number AS TEXT) = CAST(b.room_number AS TEXT)
            WHERE b.property_code = :property_code
              AND LOWER(COALESCE(b.booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
              AND b.room_number IS NOT NULL
              AND LOWER(COALESCE({status_expr}, 'unknown')) IN ('dirty', 'vacant_dirty', 'out_of_order', 'out of order', 'not_inspected', 'unknown')
            LIMIT 25
            """
        ),
        {"property_code": property_code},
    ).mappings().all()

    exceptions = [
        _exception(
            key="dirty_occupied_rooms",
            department="housekeeping",
            severity="warning",
            message=f"In-house room {row['room_number']} has housekeeping status {row['room_status']}.",
            is_blocking=False,
            override_allowed=True,
            action="Resolve Housekeeping",
            related_booking_id=row["booking_id"],
            related_room_number=str(row["room_number"]),
        )
        for row in mismatch_rows
    ]

    unavailable_count = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM rooms r
            WHERE r.property_code = :property_code
              AND LOWER(COALESCE({status_expr}, 'unknown')) IN (
                'out_of_order', 'out of order', 'ooo',
                'out_of_service', 'out of service', 'oos',
                'maintenance'
              )
            """
        ),
        {"property_code": property_code},
    ).scalar()
    if int(unavailable_count or 0):
        exceptions.append(
            _exception(
                key="rooms_out_of_order_or_service",
                department="housekeeping",
                severity="warning",
                message=f"{int(unavailable_count or 0)} room(s) are Out of Order, Out of Service, or maintenance.",
                is_blocking=False,
                override_allowed=True,
                action="Review Room Board",
                count=int(unavailable_count or 0),
            )
        )
    return exceptions


def _finance_exceptions(db: Session, property_code: str, business_date: date) -> tuple[list[dict], dict]:
    try:
        report = get_finance_control_report(
            property_code=property_code,
            business_date=business_date,
            db=db,
        )
    except Exception as exc:
        db.rollback()
        return [
            _exception(
                key="finance_control_report_unavailable",
                department="finance",
                severity="warning",
                message=f"Finance control report could not load: {exc}",
                is_blocking=False,
                override_allowed=True,
                action="Review Finance",
            )
        ], {
            "finance_dashboard": {
                "open_folios": 0,
                "guest_ledger_balance": 0,
            },
            "cashier_shift": {
                "unassigned": 0,
            },
            "finance_exceptions": [],
        }

    exceptions: list[dict] = []
    for item in report.get("finance_exceptions") or []:
        key = item.get("key") or "finance_exception"
        severity = item.get("severity") or "warning"
        is_blocking = key in {"duplicate_open_folios"} or severity == "critical"
        exceptions.append(
            _exception(
                key=key,
                department="finance",
                severity=severity,
                message=item.get("message") or "Finance exception requires review.",
                is_blocking=is_blocking,
                override_allowed=not is_blocking,
                action="Resolve Finance",
                count=item.get("count"),
            )
        )

    dashboard = report.get("finance_dashboard") or {}
    cashier = report.get("cashier_shift") or {}
    if float(cashier.get("unassigned") or 0) > 0:
        exceptions.append(
            _exception(
                key="unassigned_payments",
                department="cashier",
                severity="warning",
                message=f"{cashier.get('unassigned')} ETB is unassigned in cashier/payment method controls.",
                is_blocking=False,
                override_allowed=True,
                action="Assign Payments",
            )
        )
    if int(dashboard.get("open_folios") or 0) > 0:
        exceptions.append(
            _exception(
                key="open_folios_with_balance",
                department="finance",
                severity="critical" if float(dashboard.get("guest_ledger_balance") or 0) != 0 else "warning",
                message=(
                    "Open folios have a non-zero guest ledger balance and must be settled or transferred before close."
                    if float(dashboard.get("guest_ledger_balance") or 0) != 0
                    else "Open folios exist and should be reviewed before close."
                ),
                is_blocking=float(dashboard.get("guest_ledger_balance") or 0) != 0,
                override_allowed=float(dashboard.get("guest_ledger_balance") or 0) == 0,
                action="Open Folios",
                count=int(dashboard.get("open_folios") or 0),
            )
        )

    return exceptions, report


def _booking_hub_exceptions(db: Session, property_code: str, business_date: date) -> list[dict]:
    exceptions: list[dict] = []

    if _table_exists(db, "public_booking_requests"):
        row = db.execute(
            text(
                """
                SELECT
                  COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(booking_status, '')) = 'pending_request'
                  ) AS pending_requests,
                  COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(booking_status, '')) IN ('deposit_requested', 'deposit_required')
                      AND LOWER(COALESCE(deposit_status, 'pending')) NOT IN ('paid', 'deposit_paid')
                  ) AS deposit_requested_unpaid
                FROM public_booking_requests
                WHERE property_code = :property_code
                  AND check_in_date >= :business_date
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().first()

        pending_requests = int((row or {}).get("pending_requests") or 0)
        deposit_requested_unpaid = int((row or {}).get("deposit_requested_unpaid") or 0)

        if pending_requests:
            exceptions.append(
                _exception(
                    key="booking_hub_pending_requests_not_reviewed",
                    department="reservations",
                    severity="warning",
                    message=f"{pending_requests} public chatbot request(s) are still pending Booking Hub review.",
                    is_blocking=False,
                    override_allowed=True,
                    action="Review Booking Hub",
                    count=pending_requests,
                )
            )
        if deposit_requested_unpaid:
            exceptions.append(
                _exception(
                    key="booking_hub_deposit_requested_not_paid",
                    department="finance",
                    severity="warning",
                    message=f"{deposit_requested_unpaid} public booking request(s) have deposit requested but not paid.",
                    is_blocking=False,
                    override_allowed=True,
                    action="Follow Up Deposit",
                    count=deposit_requested_unpaid,
                )
            )

    if _table_exists(db, "bookings"):
        booking_columns = _table_columns(db, "bookings")
        amount_expr = (
            "COALESCE(total_amount, total_amount_etb, total_revenue_etb, 0)"
            if {"total_amount", "total_amount_etb", "total_revenue_etb"}.issubset(booking_columns)
            else "COALESCE(total_revenue_etb, 0)"
            if "total_revenue_etb" in booking_columns
            else "COALESCE(total_amount_etb, 0)"
            if "total_amount_etb" in booking_columns
            else "COALESCE(total_amount, 0)"
            if "total_amount" in booking_columns
            else "0"
        )
        rate_expr = "COALESCE(rate_per_night_etb, 0)" if "rate_per_night_etb" in booking_columns else "0"

        missing_rate = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM bookings
                WHERE property_code = :property_code
                  AND check_in_date >= :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee')
                  AND ({rate_expr} <= 0 OR {amount_expr} <= 0)
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()

        if int(missing_rate or 0):
            exceptions.append(
                _exception(
                    key="bookings_without_rate",
                    department="reservations",
                    severity="warning",
                    message=f"{int(missing_rate or 0)} active booking(s) are missing rate or booking value.",
                    is_blocking=False,
                    override_allowed=True,
                    action="Correct Rate",
                    count=int(missing_rate or 0),
                )
            )

        if _table_exists(db, "folios"):
            missing_folio = db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM bookings b
                    LEFT JOIN folios f
                      ON f.property_code = b.property_code
                     AND f.booking_id = b.id
                     AND COALESCE(f.status, 'open') = 'open'
                    WHERE b.property_code = :property_code
                      AND b.check_in_date >= :business_date
                      AND LOWER(COALESCE(b.booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'in_house', 'checked_in')
                      AND f.id IS NULL
                    """
                ),
                {"property_code": property_code, "business_date": business_date},
            ).scalar()
            if int(missing_folio or 0):
                exceptions.append(
                    _exception(
                        key="bookings_without_folio",
                        department="finance",
                        severity="warning",
                        message=f"{int(missing_folio or 0)} active booking(s) do not have an open folio prepared.",
                        is_blocking=False,
                        override_allowed=True,
                        action="Prepare Folio",
                        count=int(missing_folio or 0),
                    )
                )

    return exceptions


def _cashier_exceptions(db: Session, property_code: str, business_date: date) -> list[dict]:
    if not _table_exists(db, "cashier_sessions"):
        return [
            _exception(
                key="cashier_sessions_not_started",
                department="cashier",
                severity="warning",
                message="Cashier close table exists only after the first cashier close. Close the cashier shift from Finance if payments were collected.",
                is_blocking=False,
                override_allowed=True,
                action="Close Cashier Shift",
            )
        ]

    db.execute(text("ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS manager_approved_by TEXT"))
    row = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE LOWER(COALESCE(status, 'open')) = 'open') AS open_sessions,
              COUNT(*) FILTER (
                WHERE COALESCE(variance, 0) <> 0
                  AND (
                    LOWER(COALESCE(status, '')) IN ('variance_review', 'open')
                    OR manager_approved_by IS NULL
                  )
              ) AS unapproved_variance_sessions
            FROM cashier_sessions
            WHERE property_code = :property_code
              AND business_date = :business_date
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    exceptions: list[dict] = []
    if int((row or {}).get("open_sessions") or 0):
        exceptions.append(
            _exception(
                key="open_cashier_shifts",
                department="cashier",
                severity="critical",
                message="Open cashier shift(s) must be closed before Night Audit.",
                is_blocking=True,
                override_allowed=False,
                action="Close Cashier Shift",
                count=int(row["open_sessions"]),
            )
        )
    if int((row or {}).get("unapproved_variance_sessions") or 0):
        exceptions.append(
            _exception(
                key="unapproved_cashier_variance",
                department="cashier",
                severity="critical",
                message="Cashier variance requires manager approval before Night Audit close.",
                is_blocking=True,
                override_allowed=True,
                action="Review Variance",
                count=int(row["unapproved_variance_sessions"]),
            )
        )
    return exceptions


def _missing_posting_exceptions(db: Session, property_code: str, business_date: date) -> list[dict]:
    if not _table_exists(db, "bookings"):
        return []
    if not _table_exists(db, "night_audit_postings"):
        count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM bookings
                WHERE property_code = :property_code
                  AND LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
                  AND check_in_date <= :business_date
                  AND check_out_date > :business_date
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
    else:
        count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM bookings b
                LEFT JOIN night_audit_postings nap
                  ON nap.property_code = b.property_code
                 AND nap.booking_id = b.id
                 AND nap.business_date = :business_date
                 AND nap.posting_type = 'room_charge'
                WHERE b.property_code = :property_code
                  AND LOWER(COALESCE(b.booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
                  AND b.check_in_date <= :business_date
                  AND b.check_out_date > :business_date
                  AND nap.id IS NULL
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
    if not int(count or 0):
        return []
    return [
        _exception(
            key="missing_room_tax_posting",
            department="finance",
            severity="warning",
            message=f"{int(count or 0)} in-house booking(s) still need Night Audit room/tax/service posting.",
            is_blocking=False,
            override_allowed=False,
            action="Run Night Audit Posting",
            count=int(count or 0),
        )
    ]


def _fnb_exceptions(db: Session, property_code: str) -> list[dict]:
    exceptions: list[dict] = []
    if _table_exists(db, "purchase_orders"):
        pending_po_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM purchase_orders
                WHERE property_code = :property_code
                  AND UPPER(COALESCE(status, 'PENDING')) NOT IN ('RECEIVED', 'REJECTED', 'CLOSED')
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(pending_po_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_pending_purchase_orders",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(pending_po_count or 0)} F&B Purchase Order(s) are still pending approval or delivery.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Review Purchase Orders",
                    count=int(pending_po_count or 0),
                )
            )
    if _table_exists(db, "goods_received"):
        unposted_grn_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM goods_received
                WHERE property_code = :property_code
                  AND LOWER(COALESCE(approval_status, 'received')) IN ('received', 'unposted')
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(unposted_grn_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_unposted_receiving",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(unposted_grn_count or 0)} Goods Receiving Note(s) need F&B/Finance posting review.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Review Goods Receiving Notes",
                    count=int(unposted_grn_count or 0),
                )
            )
    if _table_exists(db, "inventory_movements"):
        negative_stock_rows = db.execute(
            text(
                """
                SELECT ingredient_name,
                       SUM(CASE
                           WHEN movement_type IN ('OPENING', 'PURCHASE_RECEIVED', 'ADJUSTMENT_IN') THEN quantity
                           WHEN movement_type IN ('KITCHEN_ISSUE', 'WASTAGE') THEN -quantity
                           WHEN movement_type = 'ADJUSTMENT' THEN quantity
                           ELSE 0
                       END) AS balance
                FROM inventory_movements
                WHERE property_code = :property_code
                GROUP BY ingredient_name
                HAVING SUM(CASE
                           WHEN movement_type IN ('OPENING', 'PURCHASE_RECEIVED', 'ADJUSTMENT_IN') THEN quantity
                           WHEN movement_type IN ('KITCHEN_ISSUE', 'WASTAGE') THEN -quantity
                           WHEN movement_type = 'ADJUSTMENT' THEN quantity
                           ELSE 0
                       END) < 0
                """
            ),
            {"property_code": property_code},
        ).mappings().all()
        if negative_stock_rows:
            exceptions.append(
                _exception(
                    key="fnb_negative_stock",
                    department="food_beverage",
                    severity="blocking",
                    message=f"{len(negative_stock_rows)} Main Store item(s) show negative stock.",
                    is_blocking=True,
                    override_allowed=True,
                    action="Correct Main Store Inventory",
                    count=len(negative_stock_rows),
                )
            )
    if _table_exists(db, "fnb_wastage_records"):
        waste_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM fnb_wastage_records
                WHERE property_code = :property_code
                  AND approved_by IS NULL
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(waste_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_unapproved_waste",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(waste_count or 0)} waste record(s) need approval.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Approve Waste Records",
                    count=int(waste_count or 0),
                )
            )
    if _table_exists(db, "fnb_stock_counts"):
        variance_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM fnb_stock_counts
                WHERE property_code = :property_code
                  AND ABS(COALESCE(variance_value, 0)) > 0
                  AND approved_by IS NULL
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(variance_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_high_variance",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(variance_count or 0)} stock variance record(s) need manager review.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Review Stock Variance",
                    count=int(variance_count or 0),
                )
            )
    if _table_exists(db, "recipes"):
        missing_recipe_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM recipes
                WHERE property_code = :property_code
                  AND COALESCE(total_cost, 0) <= 0
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(missing_recipe_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_missing_recipe_cost",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(missing_recipe_count or 0)} menu recipe(s) are missing recipe cost.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Complete Recipe Costing",
                    count=int(missing_recipe_count or 0),
                )
            )
    if _table_exists(db, "ingredients") and _table_exists(db, "inventory_movements"):
        stock_rows = db.execute(
            text(
                """
                SELECT
                    i.name,
                    COALESCE(i.reorder_level, 0) AS reorder_level,
                    COALESCE(i.cost_per_unit, 0) AS cost_per_unit,
                    i.expiry_date,
                    COALESCE(SUM(
                        CASE
                            WHEN UPPER(m.movement_type) IN ('OPENING', 'PURCHASE_RECEIVED', 'ADJUSTMENT_IN') THEN m.quantity
                            WHEN UPPER(m.movement_type) IN ('KITCHEN_ISSUE', 'WASTAGE') THEN -m.quantity
                            WHEN UPPER(m.movement_type) = 'ADJUSTMENT' THEN m.quantity
                            ELSE 0
                        END
                    ), 0) AS balance_on_hand
                FROM ingredients i
                LEFT JOIN inventory_movements m
                  ON m.property_code = i.property_code
                 AND m.ingredient_name = i.name
                WHERE i.property_code = :property_code
                GROUP BY i.name, i.reorder_level, i.cost_per_unit, i.expiry_date
                """
            ),
            {"property_code": property_code},
        ).mappings().all()
        expired_count = sum(1 for row in stock_rows if row["expiry_date"] and row["expiry_date"] < business_date)
        low_stock_count = sum(
            1
            for row in stock_rows
            if float(row["reorder_level"] or 0) > 0
            and float(row["balance_on_hand"] or 0) <= float(row["reorder_level"] or 0)
        )
        missing_price_count = sum(1 for row in stock_rows if float(row["cost_per_unit"] or 0) <= 0)
        for key, count, severity, message, action in [
            ("fnb_expired_stock", expired_count, "critical", "F&B Main Store item(s) are expired.", "Block expired stock issue"),
            ("fnb_low_stock", low_stock_count, "warning", "F&B Main Store item(s) are at or below reorder level.", "Create Purchase Requisition"),
            ("fnb_missing_unit_price", missing_price_count, "warning", "F&B ingredient(s) are missing unit price.", "Update Ingredient Master"),
        ]:
            if count:
                exceptions.append(
                    _exception(
                        key=key,
                        department="food_beverage",
                        severity=severity,
                        message=f"{count} {message}",
                        is_blocking=False,
                        override_allowed=False,
                        action=action,
                        count=count,
                    )
                )
    if _table_exists(db, "fnb_kitchen_requisitions"):
        open_req_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM fnb_kitchen_requisitions
                WHERE property_code = :property_code
                  AND LOWER(COALESCE(status, 'requested')) NOT IN ('issued', 'closed', 'cancelled')
                """
            ),
            {"property_code": property_code},
        ).scalar()
        if int(open_req_count or 0):
            exceptions.append(
                _exception(
                    key="fnb_open_store_requisitions",
                    department="food_beverage",
                    severity="warning",
                    message=f"{int(open_req_count or 0)} Store Requisition(s) are still open.",
                    is_blocking=False,
                    override_allowed=False,
                    action="Issue or close Store Requisitions",
                    count=int(open_req_count or 0),
                )
            )
    return exceptions


def _night_audit_exception_payload(db: Session, property_code: str, business_date: date) -> dict:
    property_code = _normalize_property_code(property_code)
    finance_exceptions, finance_report = _finance_exceptions(db, property_code, business_date)
    exceptions = [
        *_booking_hub_exceptions(db, property_code, business_date),
        *_frontdesk_exceptions(db, property_code, business_date),
        *_housekeeping_exceptions(db, property_code),
        *finance_exceptions,
        *_fnb_exceptions(db, property_code),
        *_cashier_exceptions(db, property_code, business_date),
        *_missing_posting_exceptions(db, property_code, business_date),
    ]

    blocking = [item for item in exceptions if item["is_blocking"]]
    warnings = [item for item in exceptions if not item["is_blocking"]]
    departments = {
        "frontdesk": sum(1 for item in exceptions if item["department"] == "frontdesk"),
        "reservations": sum(1 for item in exceptions if item["department"] == "reservations"),
        "housekeeping": sum(1 for item in exceptions if item["department"] == "housekeeping"),
        "finance": sum(1 for item in exceptions if item["department"] == "finance"),
        "cashier": sum(1 for item in exceptions if item["department"] == "cashier"),
        "food_beverage": sum(1 for item in exceptions if item["department"] == "food_beverage"),
    }

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "ready_to_run": len(blocking) == 0,
        "audit_status": "ready" if not blocking else "not_ready",
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "department_counts": departments,
        "blocking_exceptions": blocking,
        "warning_exceptions": warnings,
        "exceptions": exceptions,
        "finance_summary": finance_report.get("finance_dashboard"),
        "cashier_shift": finance_report.get("cashier_shift"),
    }


@router.get("/status")
def get_night_audit_status(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: Optional[date] = Query(None, description="Business date to audit"),
    db: Session = Depends(get_db),
):
    audit_date = business_date or date.today()
    next_business_date = _next_day(audit_date)
    lock_row = None
    if _table_exists(db, "business_date_locks"):
        lock_row = db.execute(
            text(
                """
                SELECT id, locked_at, locked_by, status, notes
                FROM business_date_locks
                WHERE property_code = :property_code
                  AND business_date = :business_date
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_code": _normalize_property_code(property_code), "business_date": audit_date},
        ).mappings().first()

    return {
        "property_code": property_code,
        "business_date": audit_date.isoformat(),
        "next_business_date": next_business_date.isoformat(),
        "already_run": bool(lock_row),
        "last_run": {
            "run_id": lock_row["id"],
            "run_at": lock_row["locked_at"].isoformat() if lock_row and lock_row["locked_at"] else None,
            "run_by": lock_row["locked_by"],
            "status": lock_row["status"],
            "notes": lock_row["notes"],
        } if lock_row else None,
        "operational_snapshot": _movement_snapshot(db, property_code, audit_date),
    }


@router.get("/readiness")
def get_night_audit_readiness(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: date = Query(..., description="Business date to audit"),
    db: Session = Depends(get_db),
):
    validation = _night_audit_exception_payload(db, property_code, business_date)
    department_counts = validation["department_counts"]
    checks = [
        {
            "key": "reservations",
            "label": "Booking Hub requests and guarantees reviewed",
            "status": "warning" if department_counts["reservations"] else "ready",
        },
        {
            "key": "frontdesk",
            "label": "Front Desk movement reviewed",
            "status": "blocked" if department_counts["frontdesk"] else "ready",
        },
        {
            "key": "housekeeping",
            "label": "Housekeeping room status reviewed",
            "status": "warning" if department_counts["housekeeping"] else "ready",
        },
        {
            "key": "finance",
            "label": "Finance ledgers and trial balance reviewed",
            "status": "blocked" if any(item["department"] == "finance" and item["is_blocking"] for item in validation["exceptions"]) else "warning" if department_counts["finance"] else "ready",
        },
        {
            "key": "food_beverage",
            "label": "F&B purchasing, receiving, stock, waste, variance, and recipe costs reviewed",
            "status": "blocked" if any(item["department"] == "food_beverage" and item["is_blocking"] for item in validation["exceptions"]) else "warning" if department_counts["food_beverage"] else "ready",
        },
        {
            "key": "cashier",
            "label": "Cashier shifts and payment methods reviewed",
            "status": "blocked" if any(item["department"] == "cashier" and item["is_blocking"] for item in validation["exceptions"]) else "warning" if department_counts["cashier"] else "ready",
        },
        {"key": "reports", "label": "Night Audit report package generated", "status": "pending"},
        {
            "key": "run_audit",
            "label": "Ready to lock and roll business date",
            "status": "ready" if validation["ready_to_run"] else "blocked",
        },
    ]

    return {
        "property_code": _normalize_property_code(property_code),
        "business_date": business_date.isoformat(),
        "ready": validation["ready_to_run"],
        "audit_status": validation["audit_status"],
        "blocking_count": validation["blocking_count"],
        "warning_count": validation["warning_count"],
        "checks": checks,
        "exceptions": validation["exceptions"],
    }


@router.get("/exceptions")
def get_night_audit_exceptions(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: date = Query(..., description="Business date to audit"),
    db: Session = Depends(get_db),
):
    return _night_audit_exception_payload(db, property_code, business_date)


@router.post("/run-validation")
def run_night_audit_validation(
    payload: NightAuditRunRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    audit_date = payload.business_date or date.today()
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="night_audit.run_validation",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    result = _night_audit_exception_payload(db, property_code, audit_date)
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="night_audit_validation_run",
        record_type="business_date",
        record_id=audit_date.isoformat(),
        new_value={
            "blocking_count": result["blocking_count"],
            "warning_count": result["warning_count"],
            "audit_status": result["audit_status"],
        },
    )
    db.commit()
    return result


@router.post("/generate-reports")
def generate_night_audit_reports(
    payload: NightAuditRunRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    audit_date = payload.business_date or date.today()
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="reports.archive",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    validation = _night_audit_exception_payload(db, property_code, audit_date)
    report_types = [
        "occupancy_summary",
        "revenue_summary",
        "payment_method_summary",
        "cashier_shift_summary",
        "open_balance_exception_report",
        "housekeeping_discrepancy_report",
        "no_show_report",
    ]
    report_package = _night_audit_report_package(db, property_code, audit_date)
    archive_id = _archive_night_audit_report(
        db,
        property_code,
        audit_date,
        payload.run_by or actor["email"],
        {
            "status": "generated_pre_close",
            "reports": report_package,
            "validation": {
                "ready_to_run": validation["ready_to_run"],
                "blocking_count": validation["blocking_count"],
                "warning_count": validation["warning_count"],
            },
        },
    )
    result = {
        "ok": True,
        "property_code": property_code,
        "business_date": audit_date.isoformat(),
        "status": "generated",
        "generated_by": payload.run_by,
        "reports": [
            {"report_type": report_type, "status": "generated"}
            for report_type in report_types
        ],
        "archive_id": archive_id,
        "report_package": report_package,
        "ready_to_run": validation["ready_to_run"],
        "blocking_count": validation["blocking_count"],
        "warning_count": validation["warning_count"],
    }
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="night_audit_reports_generated",
        record_type="business_date",
        record_id=audit_date.isoformat(),
        new_value={"reports": report_types, "ready_to_run": validation["ready_to_run"], "archive_id": archive_id},
    )
    db.commit()
    return result


@router.post("/run")
def run_night_audit(
    payload: NightAuditRunRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    audit_date = payload.business_date or date.today()
    next_business_date = _next_day(audit_date)
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="night_audit.run_audit",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    no_show_summary = _process_no_show_candidates(db, property_code, audit_date)
    if no_show_summary["marked_no_show"]:
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="night_audit",
            action="night_audit_no_shows_processed",
            record_type="business_date",
            record_id=audit_date.isoformat(),
            new_value=no_show_summary,
        )
    validation = _night_audit_exception_payload(db, property_code, audit_date)

    if not validation["ready_to_run"]:
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="night_audit",
            action="night_audit_run_blocked",
            record_type="business_date",
            record_id=audit_date.isoformat(),
            new_value={
                "blocking_count": validation["blocking_count"],
                "warning_count": validation["warning_count"],
            },
        )
        db.commit()
        return {
            "ok": False,
            "status": "validation_failed",
            "property_code": property_code,
            "closed_business_date": audit_date.isoformat(),
            "next_business_date": audit_date.isoformat(),
            "run_by": payload.run_by,
            "message": "Night Audit cannot run until blocking exceptions are resolved.",
            "blocking_exceptions": validation["blocking_exceptions"],
            "warning_exceptions": validation["warning_exceptions"],
            "no_show_summary": no_show_summary,
        }

    posting_summary = _post_nightly_charges(db, property_code, audit_date)
    report_package = _night_audit_report_package(db, property_code, audit_date)
    close_payload = {
        "property_code": property_code,
        "closed_business_date": audit_date.isoformat(),
        "next_business_date": next_business_date.isoformat(),
        "posting_summary": posting_summary,
        "no_show_summary": no_show_summary,
        "reports": report_package,
        "audit_summary": {
            "occupancy": report_package.get("occupancy_summary"),
            "revenue": report_package.get("revenue_summary"),
            "cashier": report_package.get("cashier_shift_summary"),
            "open_balance_exceptions": len(report_package.get("open_balance_exception_report") or []),
            "housekeeping_discrepancies": len(report_package.get("housekeeping_discrepancy_report") or []),
            "no_shows": len(report_package.get("no_show_report") or []),
        },
        "finance_summary": validation.get("finance_summary"),
        "warning_count": validation["warning_count"],
    }
    archive_id = _archive_night_audit_report(
        db,
        property_code,
        audit_date,
        payload.run_by or actor["email"],
        close_payload,
    )
    _lock_business_date(
        db,
        property_code,
        audit_date,
        payload.run_by or actor["email"],
        payload.notes,
    )
    property_date_rolled = _roll_property_business_date(db, property_code, next_business_date)
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="business_date_locked",
        record_type="business_date",
        record_id=audit_date.isoformat(),
        new_value={
            "closed_by": payload.run_by or actor["email"],
            "closed_at": "now",
            "next_business_date": next_business_date.isoformat(),
            "property_date_rolled": property_date_rolled,
        },
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="night_audit_run_completed",
        record_type="business_date",
        record_id=audit_date.isoformat(),
        new_value={
            "next_business_date": next_business_date.isoformat(),
            "posting_summary": posting_summary,
            "no_show_summary": no_show_summary,
            "archive_id": archive_id,
            "property_date_rolled": property_date_rolled,
        },
    )
    db.commit()
    return {
        "ok": True,
        "status": "completed",
        "property_code": property_code,
        "closed_business_date": audit_date.isoformat(),
        "next_business_date": next_business_date.isoformat(),
        "run_by": payload.run_by,
        "message": "Night Audit completed. Front Desk, Finance, Cashier, and Housekeeping controls are ready for business date rollover.",
        "posting_summary": posting_summary,
        "no_show_summary": no_show_summary,
        "report_package": report_package,
        "property_date_rolled": property_date_rolled,
        "archive_id": archive_id,
    }


@router.post("/override-exception")
def override_night_audit_exception(
    payload: NightAuditOverrideRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="night_audit.override_exception",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="night_audit_exception_overridden",
        record_type="night_audit_exception",
        record_id=payload.exception_key,
        new_value={
            "business_date": payload.business_date.isoformat(),
            "override_reason": payload.override_reason,
        },
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="night_audit_manager_override",
        record_type="night_audit_exception",
        record_id=payload.exception_key,
        new_value={
            "business_date": payload.business_date.isoformat(),
            "override_reason": payload.override_reason,
        },
    )
    db.commit()
    return {
        "ok": True,
        "property_code": property_code,
        "business_date": payload.business_date.isoformat(),
        "exception_key": payload.exception_key,
        "override_by": payload.override_by,
        "message": "Manager override recorded for review workflow. Persistent override storage should be enabled in production migration.",
    }


@router.patch("/business-date")
def override_business_date(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: date = Query(..., description="Business date to set"),
    reason: str | None = Query(None, description="Manager/admin reason for reopening or adjustment"),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    actor = require_pms_permission(
        db,
        permission_key="night_audit.override_exception",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    ensure_business_date_lock_table(db)
    reopen_business_date(
        db,
        property_code=property_code,
        business_date=business_date,
        reopened_by=actor["email"],
        reason=reason or "Business date adjustment",
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="night_audit",
        action="business_date_reopen_adjustment_attempt",
        record_type="business_date",
        record_id=business_date.isoformat(),
        new_value={"business_date": business_date.isoformat(), "reason": reason},
    )
    db.commit()
    return {
        "ok": True,
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "message": "Business date override accepted.",
    }
