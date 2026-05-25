from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db

router = APIRouter(prefix="/night-audit", tags=["night-audit"])


class NightAuditRunRequest(BaseModel):
    property_code: str
    business_date: Optional[date] = None
    run_by: Optional[str] = None
    notes: Optional[str] = None


def _next_day(value: date) -> date:
    return value + timedelta(days=1)


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


@router.get("/status")
def get_night_audit_status(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: Optional[date] = Query(None, description="Business date to audit"),
    db: Session = Depends(get_db),
):
    audit_date = business_date or date.today()
    next_business_date = _next_day(audit_date)

    return {
        "property_code": property_code,
        "business_date": audit_date.isoformat(),
        "next_business_date": next_business_date.isoformat(),
        "already_run": False,
        "last_run": None,
        "operational_snapshot": _movement_snapshot(db, property_code, audit_date),
    }


@router.get("/readiness")
def get_night_audit_readiness(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: date = Query(..., description="Business date to audit"),
):
    checks = [
        {"key": "arrivals", "label": "Arrivals reviewed", "status": "pending"},
        {"key": "departures", "label": "Departures reviewed", "status": "pending"},
        {"key": "folios", "label": "Open folios reviewed", "status": "pending"},
        {
            "key": "housekeeping",
            "label": "Housekeeping room status reviewed",
            "status": "pending",
        },
    ]

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "ready": False,
        "checks": checks,
    }


@router.post("/run")
def run_night_audit(payload: NightAuditRunRequest):
    audit_date = payload.business_date or date.today()
    next_business_date = _next_day(audit_date)

    return {
        "ok": True,
        "status": "accepted",
        "property_code": payload.property_code,
        "closed_business_date": audit_date.isoformat(),
        "next_business_date": next_business_date.isoformat(),
        "run_by": payload.run_by,
        "message": "Night audit workflow accepted and business date is ready to roll forward.",
    }


@router.patch("/business-date")
def override_business_date(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    business_date: date = Query(..., description="Business date to set"),
):
    return {
        "ok": True,
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "message": "Business date override accepted.",
    }
