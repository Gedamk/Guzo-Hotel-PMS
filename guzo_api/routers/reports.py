# -*- coding: utf-8 -*-
"""
guzo_api.routers.reports – Reporting endpoints
---------------------------------------------
Exposes JSON endpoints for:
 - /reports/daily
 - /reports/monthly
 - /reports/portfolio
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from guzo_api.auth_deps import get_current_user, User
from guzo_backend.modules.reports_daily_manager import get_daily_manager_report
from guzo_backend.modules.reports_monthly_owner import get_monthly_owner_report
from guzo_backend.modules.reports_portfolio_owner import get_portfolio_owner_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _check_property_permission(user: User, property_code: Optional[str]) -> None:
    """
    Enforce that the user is allowed to access the given property.
    """
    if not property_code:
        return

    allowed = user.allowed_properties or []
    if "ALL" in allowed:
        return

    if property_code not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Not allowed to view property {property_code}",
        )


@router.get("/daily")
def daily_report(
    date: datetime.date,
    property_code: str,
    user: User = Depends(get_current_user),
):
    """
    GET /reports/daily?date=YYYY-MM-DD&property_code=DRE001

    Returns the same structure as reports_daily_manager.get_daily_manager_report().
    """
    _check_property_permission(user, property_code)

    report = get_daily_manager_report(date, property_code=property_code)
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No daily report data for this date/property.",
        )
    return {
        "scope": "single_property",
        "property_code": property_code,
        "date": str(date),
        "report": report,
    }


@router.get("/monthly")
def monthly_report(
    year: int,
    month: int,
    property_code: str,
    user: User = Depends(get_current_user),
):
    """
    GET /reports/monthly?year=2025&month=11&property_code=DRE001

    Returns the same structure as reports_monthly_owner.get_monthly_owner_report().
    """
    _check_property_permission(user, property_code)

    report = get_monthly_owner_report(year=year, month=month, property_code=property_code)
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No monthly report data for this month/property.",
        )
    return {
        "scope": "single_property",
        "property_code": property_code,
        "year": year,
        "month": month,
        "report": report,
    }


@router.get("/portfolio")
def portfolio_report(
    year: int,
    month: Optional[int] = None,
    user: User = Depends(get_current_user),
):
    """
    GET /reports/portfolio?year=2025&month=11
    or
    GET /reports/portfolio?year=2025  (full year)

    For now, uses all properties available in Postgres.
    Later, you can filter inside get_portfolio_owner_report
    based on user.allowed_properties.
    """
    report = get_portfolio_owner_report(year=year, month=month)
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No portfolio data for this period.",
        )
    return {
        "scope": "portfolio",
        "year": year,
        "month": month,
        "report": report,
    }
