# -*- coding: utf-8 -*-
"""
routes_reports.py – API endpoints for portfolio & hotel room reports
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.modules.reports_postgres import (
    build_portfolio_report,
    build_hotel_report,
)
from guzo_backend.services.pms_security_service import require_global_admin, require_property_access

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/portfolio")
def get_portfolio_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Portfolio-level monthly room report.
    Example:
        GET /reports/portfolio?year=2025&month=11
    """
    require_global_admin(db, user_email=x_pms_user_email)
    try:
        report = build_portfolio_report(year, month)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hotel/{property_code}")
def get_hotel_monthly_report(
    property_code: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Single-hotel monthly room report.
    Example:
        GET /reports/hotel/DRE001?year=2025&month=11
    """
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    try:
        report = build_hotel_report(property_code, year, month)
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"No report found for property_code={property_code} in {year}-{month:02d}",
            )
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
