# -*- coding: utf-8 -*-
"""
routes_reports.py – API endpoints for portfolio & hotel room reports
"""

from fastapi import APIRouter, HTTPException, Query

from guzo_backend.modules.reports_postgres import (
    build_portfolio_report,
    build_hotel_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/portfolio")
def get_portfolio_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    """
    Portfolio-level monthly room report.
    Example:
        GET /reports/portfolio?year=2025&month=11
    """
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
):
    """
    Single-hotel monthly room report.
    Example:
        GET /reports/hotel/DRE001?year=2025&month=11
    """
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
