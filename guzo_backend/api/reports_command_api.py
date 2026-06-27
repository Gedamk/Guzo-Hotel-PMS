from __future__ import annotations

import json
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.api.finance_api import get_finance_control_report
from guzo_backend.api.night_audit_api import _night_audit_exception_payload
from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import (
    record_pms_audit_log,
    require_pms_permission,
    require_property_access,
)

router = APIRouter(prefix="/reports", tags=["reports-command"])


class ReportArchiveIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    report_key: str = Field("daily_manager", min_length=1)
    report_name: str = Field("Daily Manager Report", min_length=1)
    report_type: str = Field("json", min_length=1)
    status: str = Field("generated", min_length=1)
    generated_by: str | None = None
    parameters_json: dict[str, Any] | None = None
    report_payload: dict[str, Any] | None = None
    file_path: str | None = None


class ScheduledReportIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    report_key: str = Field(..., min_length=1)
    report_name: str = Field(..., min_length=1)
    recipient_email: str = Field(..., min_length=3)
    frequency: str = Field("daily", min_length=1)
    schedule_time: str = Field("07:00", min_length=4)
    is_active: bool = True


class ReportEmailIn(BaseModel):
    property_code: str = Field(..., min_length=1)
    business_date: date
    recipient_email: str = Field(..., min_length=3)
    generated_by: str | None = None
    message: str | None = None


REPORT_REGISTRY = [
    ("daily_manager", "Daily Manager Report", "Executive", "Daily operating truth for the General Manager.", "/reports/command-center", True, True, True, True, "manager"),
    ("operations_summary", "Operations Summary", "Executive", "Rooms, arrivals, departures, housekeeping, and exceptions.", "/reports/command-center", True, True, True, True, "manager"),
    ("expected_checkins", "Expected Check-Ins", "Front Desk", "Guests expected to arrive for the business date.", "/reports/command-center", True, True, False, True, "frontdesk"),
    ("in_house_guests", "In-House Guests", "Front Desk", "Current in-house guest movement report.", "/reports/command-center", True, True, False, True, "frontdesk"),
    ("pending_guarantee", "Pending Guarantee Report", "Reservations", "Reservations requiring deposit, card guarantee, or approval.", "/reports/command-center", True, True, True, True, "reservations"),
    ("booking_hub_conversion", "Booking Hub Conversion Report", "Reservations", "Chatbot/public requests, converted bookings, rejected requests, deposits, and channel conversion.", "/reports/command-center", True, True, True, True, "reservations"),
    ("room_status", "Room Status Report", "Housekeeping", "Clean, dirty, occupied, vacant, and out-of-order room report.", "/reports/command-center", True, True, False, True, "housekeeping"),
    ("daily_revenue", "Daily Revenue Report", "Finance", "Revenue, tax, service charge, refunds, and payment summary.", "/finance/control-report", True, True, True, True, "accounting"),
    ("trial_balance", "Trial Balance", "Finance", "Guest ledger, deposit ledger, AR, revenue, payments, and closing balance.", "/finance/control-report", True, True, True, True, "accounting"),
    ("payment_ledger", "Payment Ledger", "Finance", "Cash, card, mobile, bank, and unassigned payment controls.", "/finance/control-report", True, True, True, True, "accounting"),
    ("night_audit_package", "Night Audit Package", "Night Audit", "Readiness, exceptions, finance controls, and end-of-day package.", "/night-audit/exceptions", True, True, True, True, "manager"),
    ("exception_summary", "Exception Summary", "Exceptions", "Blocking and warning exceptions by department.", "/night-audit/exceptions", True, True, True, True, "manager"),
    ("telegram_bookings", "Telegram Booking Report", "Channels", "Telegram reservations, pending guarantees, and source performance.", "/reports/command-center", True, True, False, True, "reservations"),
]


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


def _money(value: Any) -> float:
    return float(value or 0)


def _ensure_report_archive_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS report_archive (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                report_key VARCHAR(100) NOT NULL,
                report_name VARCHAR(200) NOT NULL,
                report_type VARCHAR(50) DEFAULT 'json',
                status VARCHAR(50) DEFAULT 'generated',
                generated_by VARCHAR(100),
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters_json JSONB,
                report_payload JSONB,
                file_path TEXT
            )
            """
        )
    )


def _ensure_scheduled_reports_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS scheduled_reports (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                report_key VARCHAR(100) NOT NULL,
                report_name VARCHAR(200) NOT NULL,
                recipient_email VARCHAR(255) NOT NULL,
                frequency VARCHAR(50) DEFAULT 'daily',
                schedule_time TIME DEFAULT '07:00',
                is_active BOOLEAN DEFAULT TRUE,
                last_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _report_name_for_key(report_key: str) -> str:
    for key, name, *_ in REPORT_REGISTRY:
        if key == report_key:
            return name
    return report_key.replace("_", " ").title()


def _booking_summary(db: Session, property_code: str, business_date: date) -> dict[str, Any]:
    if not _table_exists(db, "bookings"):
        return {
            "rooms_sold": 0,
            "arrivals": 0,
            "departures": 0,
            "in_house": 0,
            "no_show_candidates": 0,
            "pending_guarantees": 0,
            "cancellations": 0,
            "telegram_bookings": 0,
            "channel_rows": [],
        }

    booking_columns = _table_columns(db, "bookings")
    source_expr = "COALESCE(source, channel, 'direct')"
    if "source" in booking_columns and "channel" not in booking_columns:
        source_expr = "COALESCE(source, 'direct')"
    elif "channel" in booking_columns and "source" not in booking_columns:
        source_expr = "COALESCE(channel, 'direct')"
    elif "source" not in booking_columns and "channel" not in booking_columns:
        source_expr = "'direct'"
    if "total_amount" in booking_columns:
        amount_expr = "COALESCE(total_amount, 0)"
    elif "total_revenue_etb" in booking_columns:
        amount_expr = "COALESCE(total_revenue_etb, 0)"
    elif "total_amount_etb" in booking_columns:
        amount_expr = "COALESCE(total_amount_etb, 0)"
    else:
        amount_expr = "0"

    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) NOT IN ('cancelled', 'no_show', 'no-show')
                  AND check_in_date <= :business_date
                  AND check_out_date > :business_date
              ) AS rooms_sold,
              COUNT(*) FILTER (WHERE check_in_date = :business_date) AS arrivals,
              COUNT(*) FILTER (WHERE check_out_date = :business_date) AS departures,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) IN ('checked in', 'checked_in', 'in_house')
              ) AS in_house,
              COUNT(*) FILTER (
                WHERE check_in_date = :business_date
                  AND LOWER(COALESCE(booking_status, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'pending')
              ) AS no_show_candidates,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) = 'pending_guarantee'
              ) AS pending_guarantees,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) = 'cancelled'
              ) AS cancellations,
              COUNT(*) FILTER (
                WHERE LOWER({source_expr}) LIKE '%telegram%'
              ) AS telegram_bookings
            FROM bookings
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()

    channel_rows = db.execute(
        text(
            f"""
            SELECT
              LOWER({source_expr}) AS source,
              COUNT(*) AS count,
              COALESCE(SUM({amount_expr}), 0) AS booking_value
            FROM bookings
            WHERE property_code = :property_code
            GROUP BY LOWER({source_expr})
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        ),
        {"property_code": property_code},
    ).mappings().all()

    return {
        "rooms_sold": int((row or {}).get("rooms_sold") or 0),
        "arrivals": int((row or {}).get("arrivals") or 0),
        "departures": int((row or {}).get("departures") or 0),
        "in_house": int((row or {}).get("in_house") or 0),
        "no_show_candidates": int((row or {}).get("no_show_candidates") or 0),
        "pending_guarantees": int((row or {}).get("pending_guarantees") or 0),
        "cancellations": int((row or {}).get("cancellations") or 0),
        "telegram_bookings": int((row or {}).get("telegram_bookings") or 0),
        "channel_rows": [
            {
                "source": channel["source"],
                "count": int(channel["count"] or 0),
                "booking_value": _money(channel["booking_value"]),
            }
            for channel in channel_rows
        ],
    }


def _booking_hub_summary(db: Session, property_code: str, business_date: date) -> dict[str, Any]:
    if not _table_exists(db, "public_booking_requests"):
        return {
            "total_requests": 0,
            "open_requests": 0,
            "converted_requests": 0,
            "rejected_requests": 0,
            "deposit_requested": 0,
            "conversion_rate_pct": 0,
            "source_rows": [],
        }

    row = db.execute(
        text(
            """
            SELECT
              COUNT(*) AS total_requests,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) IN ('pending_request', 'reviewed', 'tentative', 'deposit_requested', 'deposit_required')
              ) AS open_requests,
              COUNT(*) FILTER (
                WHERE converted_booking_id IS NOT NULL OR LOWER(COALESCE(booking_status, '')) = 'converted'
              ) AS converted_requests,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) = 'rejected'
              ) AS rejected_requests,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) IN ('deposit_requested', 'deposit_required')
              ) AS deposit_requested
            FROM public_booking_requests
            WHERE property_code = :property_code
              AND created_at::date <= :business_date
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()

    source_rows = db.execute(
        text(
            """
            SELECT
              LOWER(COALESCE(channel, source, 'public_request')) AS source,
              COUNT(*) AS requests,
              COUNT(*) FILTER (
                WHERE converted_booking_id IS NOT NULL OR LOWER(COALESCE(booking_status, '')) = 'converted'
              ) AS conversions,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) = 'rejected'
              ) AS rejected,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(booking_status, '')) IN ('deposit_requested', 'deposit_required')
              ) AS deposit_requested
            FROM public_booking_requests
            WHERE property_code = :property_code
            GROUP BY LOWER(COALESCE(channel, source, 'public_request'))
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        ),
        {"property_code": property_code},
    ).mappings().all()

    total_requests = int((row or {}).get("total_requests") or 0)
    converted_requests = int((row or {}).get("converted_requests") or 0)
    conversion_rate = round((converted_requests / total_requests) * 100, 2) if total_requests else 0

    return {
        "total_requests": total_requests,
        "open_requests": int((row or {}).get("open_requests") or 0),
        "converted_requests": converted_requests,
        "rejected_requests": int((row or {}).get("rejected_requests") or 0),
        "deposit_requested": int((row or {}).get("deposit_requested") or 0),
        "conversion_rate_pct": conversion_rate,
        "source_rows": [
            {
                "source": source["source"],
                "requests": int(source["requests"] or 0),
                "conversions": int(source["conversions"] or 0),
                "rejected": int(source["rejected"] or 0),
                "deposit_requested": int(source["deposit_requested"] or 0),
                "conversion_rate_pct": round((int(source["conversions"] or 0) / int(source["requests"] or 1)) * 100, 2),
            }
            for source in source_rows
        ],
    }


def _room_summary(db: Session, property_code: str) -> dict[str, int]:
    if not _table_exists(db, "rooms"):
        return {
            "rooms_available": 0,
            "vacant_clean": 0,
            "vacant_dirty": 0,
            "occupied_dirty": 0,
            "out_of_order": 0,
            "housekeeping_exceptions": 0,
        }

    room_columns = _table_columns(db, "rooms")
    status_expr = "status" if "status" in room_columns else "housekeeping_status" if "housekeeping_status" in room_columns else "'unknown'"

    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) AS rooms_available,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({status_expr}, '')) IN ('clean', 'vacant_clean', 'inspected')) AS vacant_clean,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({status_expr}, '')) IN ('dirty', 'vacant_dirty')) AS vacant_dirty,
              COUNT(*) FILTER (WHERE LOWER(COALESCE({status_expr}, '')) IN ('out_of_order', 'out of order', 'out_of_service')) AS out_of_order
            FROM rooms
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code},
    ).mappings().first()
    return {
        "rooms_available": int((row or {}).get("rooms_available") or 0),
        "vacant_clean": int((row or {}).get("vacant_clean") or 0),
        "vacant_dirty": int((row or {}).get("vacant_dirty") or 0),
        "occupied_dirty": 0,
        "out_of_order": int((row or {}).get("out_of_order") or 0),
        "housekeeping_exceptions": int((row or {}).get("vacant_dirty") or 0) + int((row or {}).get("out_of_order") or 0),
    }


@router.get("/registry")
def get_report_registry():
    return [
        {
            "report_key": key,
            "report_name": name,
            "module": module,
            "description": description,
            "endpoint": endpoint,
            "supports_print": supports_print,
            "supports_csv": supports_csv,
            "supports_pdf": supports_pdf,
            "supports_schedule": supports_schedule,
            "role_required": role_required,
        }
        for key, name, module, description, endpoint, supports_print, supports_csv, supports_pdf, supports_schedule, role_required in REPORT_REGISTRY
    ]


@router.get("/command-center")
def get_reports_command_center(
    property_code: str = Query(...),
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    bookings = _booking_summary(db, property_code, business_date)
    booking_hub = _booking_hub_summary(db, property_code, business_date)
    rooms = _room_summary(db, property_code)
    finance = get_finance_control_report(
        property_code=property_code,
        business_date=business_date,
        db=db,
        x_pms_user_email=x_pms_user_email,
    )
    night_audit = _night_audit_exception_payload(db, property_code, business_date)
    archive_rows = _get_report_archive_rows(db, property_code, business_date)
    scheduled_rows = _get_scheduled_report_rows(db, property_code)

    rooms_available = rooms["rooms_available"]
    rooms_sold = bookings["rooms_sold"]
    gross_revenue = _money((finance.get("finance_dashboard") or {}).get("gross_booking_value"))
    payments_collected = _money((finance.get("finance_dashboard") or {}).get("payments_collected"))
    occupancy_pct = round((rooms_sold / rooms_available) * 100, 2) if rooms_available else 0
    adr = round(gross_revenue / rooms_sold, 2) if rooms_sold else 0
    revpar = round(gross_revenue / rooms_available, 2) if rooms_available else 0

    kpis = {
        "rooms_sold": rooms_sold,
        "rooms_available": rooms_available,
        "occupancy_pct": occupancy_pct,
        "adr": adr,
        "revpar": revpar,
        "gross_revenue": gross_revenue,
        "payments_collected": payments_collected,
        "pending_payments": _money((finance.get("finance_dashboard") or {}).get("pending_payments")),
        "pending_guarantees": bookings["pending_guarantees"],
        "guest_ledger_balance": _money((finance.get("finance_dashboard") or {}).get("guest_ledger_balance")),
        "deposit_ledger_balance": _money((finance.get("finance_dashboard") or {}).get("deposit_ledger_balance")),
        "open_folios": int((finance.get("finance_dashboard") or {}).get("open_folios") or 0),
        "open_exceptions": int(night_audit.get("blocking_count") or 0) + int(night_audit.get("warning_count") or 0),
        "night_audit_status": night_audit.get("audit_status"),
        "booking_hub_requests": booking_hub["total_requests"],
        "booking_hub_conversions": booking_hub["converted_requests"],
        "booking_hub_conversion_rate_pct": booking_hub["conversion_rate_pct"],
    }

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "generated_at": date.today().isoformat(),
        "kpis": kpis,
        "executive_summary": {
            "daily_manager_report": "ready",
            "operations_summary": "ready",
            "night_audit_status": night_audit.get("audit_status"),
            "management_attention": night_audit.get("exceptions", [])[:8],
        },
        "frontdesk": {
            "arrivals": bookings["arrivals"],
            "departures": bookings["departures"],
            "in_house": bookings["in_house"],
            "no_show_candidates": bookings["no_show_candidates"],
        },
        "reservations": {
            "pending_guarantees": bookings["pending_guarantees"],
            "cancellations": bookings["cancellations"],
            "telegram_bookings": bookings["telegram_bookings"],
            "booking_hub": booking_hub,
        },
        "housekeeping": rooms,
        "finance": finance,
        "night_audit": night_audit,
        "revenue": {
            "occupancy_pct": occupancy_pct,
            "adr": adr,
            "revpar": revpar,
            "gross_revenue": gross_revenue,
        },
        "channels": bookings["channel_rows"],
        "booking_hub_channels": booking_hub["source_rows"],
        "exceptions": night_audit.get("exceptions", []),
        "archive": archive_rows,
        "scheduled": scheduled_rows,
        "registry": get_report_registry(),
    }


def _get_report_archive_rows(
    db: Session,
    property_code: str,
    business_date: date | None = None,
) -> list[dict[str, Any]]:
    if not _table_exists(db, "report_archive"):
        return []

    date_filter = "AND business_date = :business_date" if business_date else ""
    rows = db.execute(
        text(
            f"""
            SELECT
              id,
              property_code,
              business_date,
              report_key,
              report_name,
              report_type,
              status,
              generated_by,
              generated_at,
              file_path
            FROM report_archive
            WHERE property_code = :property_code
              {date_filter}
            ORDER BY generated_at DESC, id DESC
            LIMIT 100
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "property_code": row["property_code"],
            "business_date": row["business_date"].isoformat() if row["business_date"] else None,
            "report_key": row["report_key"],
            "report_name": row["report_name"],
            "report_type": row["report_type"],
            "status": row["status"],
            "generated_by": row["generated_by"],
            "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
            "file_path": row["file_path"],
        }
        for row in rows
    ]


def _get_scheduled_report_rows(db: Session, property_code: str) -> list[dict[str, Any]]:
    if not _table_exists(db, "scheduled_reports"):
        return []

    rows = db.execute(
        text(
            """
            SELECT
              id,
              property_code,
              report_key,
              report_name,
              recipient_email,
              frequency,
              schedule_time,
              is_active,
              last_sent_at,
              created_at
            FROM scheduled_reports
            WHERE property_code = :property_code
            ORDER BY is_active DESC, schedule_time, id DESC
            LIMIT 100
            """
        ),
        {"property_code": property_code},
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "property_code": row["property_code"],
            "report_key": row["report_key"],
            "report_name": row["report_name"],
            "recipient_email": row["recipient_email"],
            "frequency": row["frequency"],
            "schedule_time": str(row["schedule_time"]) if row["schedule_time"] else None,
            "is_active": bool(row["is_active"]),
            "last_sent_at": row["last_sent_at"].isoformat() if row["last_sent_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.post("/archive")
def archive_report(
    payload: ReportArchiveIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="reports.archive",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    report_payload = payload.report_payload or get_reports_command_center(
        property_code=property_code,
        business_date=payload.business_date,
        db=db,
    )
    parameters_json = payload.parameters_json or {
        "property_code": property_code,
        "business_date": payload.business_date.isoformat(),
        "report_key": payload.report_key,
    }

    try:
        _ensure_report_archive_table(db)
        created = db.execute(
            text(
                """
                INSERT INTO report_archive(
                  property_code,
                  business_date,
                  report_key,
                  report_name,
                  report_type,
                  status,
                  generated_by,
                  parameters_json,
                  report_payload,
                  file_path
                )
                VALUES(
                  :property_code,
                  :business_date,
                  :report_key,
                  :report_name,
                  :report_type,
                  :status,
                  :generated_by,
                  CAST(:parameters_json AS JSONB),
                  CAST(:report_payload AS JSONB),
                  :file_path
                )
                RETURNING id, generated_at
                """
            ),
            {
                "property_code": property_code,
                "business_date": payload.business_date,
                "report_key": payload.report_key,
                "report_name": payload.report_name or _report_name_for_key(payload.report_key),
                "report_type": payload.report_type,
                "status": payload.status,
                "generated_by": payload.generated_by,
                "parameters_json": json.dumps(parameters_json, default=str),
                "report_payload": json.dumps(report_payload, default=str),
                "file_path": payload.file_path,
            },
        ).mappings().first()
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="reports",
            action="report_archived",
            record_type="report_archive",
            record_id=int(created["id"]),
            new_value={
                "business_date": payload.business_date.isoformat(),
                "report_key": payload.report_key,
                "report_name": payload.report_name,
                "status": payload.status,
            },
        )
        db.commit()
        return {
            "ok": True,
            "archive_id": int(created["id"]),
            "generated_at": created["generated_at"].isoformat() if created["generated_at"] else None,
            "message": "Report archived successfully.",
        }
    except Exception:
        db.rollback()
        raise


@router.get("/archive")
def get_report_archive(
    property_code: str = Query(...),
    business_date: date | None = Query(None),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return {
        "property_code": property_code,
        "business_date": business_date.isoformat() if business_date else None,
        "rows": _get_report_archive_rows(db, property_code, business_date),
    }


@router.post("/schedule")
def schedule_report(
    payload: ScheduledReportIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="reports.schedule",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    try:
        _ensure_scheduled_reports_table(db)
        created = db.execute(
            text(
                """
                INSERT INTO scheduled_reports(
                  property_code,
                  report_key,
                  report_name,
                  recipient_email,
                  frequency,
                  schedule_time,
                  is_active
                )
                VALUES(
                  :property_code,
                  :report_key,
                  :report_name,
                  :recipient_email,
                  :frequency,
                  CAST(:schedule_time AS TIME),
                  :is_active
                )
                RETURNING id
                """
            ),
            {
                "property_code": property_code,
                "report_key": payload.report_key,
                "report_name": payload.report_name or _report_name_for_key(payload.report_key),
                "recipient_email": payload.recipient_email,
                "frequency": payload.frequency,
                "schedule_time": payload.schedule_time,
                "is_active": payload.is_active,
            },
        ).mappings().first()
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="reports",
            action="report_scheduled",
            record_type="scheduled_report",
            record_id=int(created["id"]),
            new_value={
                "report_key": payload.report_key,
                "recipient_email": payload.recipient_email,
                "frequency": payload.frequency,
                "schedule_time": payload.schedule_time,
                "is_active": payload.is_active,
            },
        )
        db.commit()
        return {
            "ok": True,
            "schedule_id": int(created["id"]),
            "message": "Scheduled report saved.",
        }
    except Exception:
        db.rollback()
        raise


@router.get("/scheduled")
def get_scheduled_reports(
    property_code: str = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return {
        "property_code": property_code,
        "rows": _get_scheduled_report_rows(db, property_code),
    }


@router.post("/{report_key}/email")
def email_report_placeholder(
    report_key: str,
    payload: ReportEmailIn,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(payload.property_code)
    actor = require_pms_permission(
        db,
        permission_key="reports.email_manager",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="reports",
        action="manager_report_email_queued",
        record_type="report_email",
        record_id=report_key,
        new_value={
            "business_date": payload.business_date.isoformat(),
            "recipient_email": payload.recipient_email,
            "message": payload.message,
        },
    )
    db.commit()
    return {
        "ok": True,
        "report_key": report_key,
        "property_code": property_code,
        "business_date": payload.business_date.isoformat(),
        "recipient_email": payload.recipient_email,
        "status": "queued",
        "message": "Manager report email queued for delivery workflow.",
    }


@router.get("/{report_key}/export.csv")
def export_report_csv_placeholder(
    report_key: str,
    property_code: str = Query(...),
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return {
        "ok": True,
        "report_key": report_key,
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "status": "csv_ready_from_frontend",
        "message": "Use the Reports Command Center CSV export for the current report table.",
    }


@router.get("/{report_key}/export.pdf")
def export_report_pdf_placeholder(
    report_key: str,
    property_code: str = Query(...),
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return {
        "ok": True,
        "report_key": report_key,
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "status": "pdf_placeholder",
        "message": "PDF generation endpoint is reserved for the next report renderer build.",
    }
