# -*- coding: utf-8 -*-
"""
reports.py – FastAPI router for Portfolio & Hotel Reports

This router:
- Protects endpoints with a simple Bearer admin token
- Uses reports_service.build_portfolio_report(...) for portfolio data
- Uses reports_service.build_hotel_report_from_portfolio(...) for hotel-level data
- Supports alias "NN002" → "N&N002" so you can avoid %26 in URLs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from guzo_api.services.reports_service import (
    build_portfolio_report,
    build_hotel_report_from_portfolio,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# -------------------------------------------------
# Simple Bearer auth (same as before)
# -------------------------------------------------
bearer_scheme = HTTPBearer()
ADMIN_SECRET = "<REDACTED_DEMO_BEARER_TOKEN>"  # later you can move this to env


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> bool:
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth scheme; expected Bearer",
        )
    if credentials.credentials != ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
    return True


# -------------------------------------------------
# Alias map for property codes
# -------------------------------------------------
PROPERTY_CODE_ALIASES = {
    # friendly alias  → real code inside portfolio report
    "NN002": "N&N002",
}


def normalize_property_code(code: str) -> str:
    """
    Convert friendly aliases to real codes (e.g. NN002 → N&N002).
    If no alias exists, return code unchanged.
    """
    return PROPERTY_CODE_ALIASES.get(code, code)


# -------------------------------------------------
# Portfolio endpoint (all hotels)
# -------------------------------------------------
@router.get("/portfolio")
def get_portfolio_report(
    year: int,
    month: int,
    _: bool = Depends(verify_admin_token),
):
    """
    Portfolio-level report for all hotels.
    Currently:
      - For 2025-11 → returns fixed demo data (from reports_service.PORTFOLIO_2025_11)
      - For other months → returns an empty portfolio structure
    """
    return build_portfolio_report(year=year, month=month)


# -------------------------------------------------
# Hotel-level endpoint (single property)
# -------------------------------------------------
@router.get("/hotel")
def get_hotel_report(
    property_code: str,
    year: int,
    month: int,
    _: bool = Depends(verify_admin_token),
):
    """
    Hotel-level report for a single property.

    - Accepts either the real property_code ("DRE001", "N&N002")
      or friendly alias ("NN002").
    - Uses the same underlying portfolio payload.
    """

    normalized_code = normalize_property_code(property_code)

    # 1) Get portfolio payload (for now still the fixed 2025-11 demo or empty)
    portfolio_payload = build_portfolio_report(year=year, month=month)

    # 2) Slice out hotel-level view
    try:
        hotel_report = build_hotel_report_from_portfolio(
            portfolio_payload=portfolio_payload,
            property_code=normalized_code,
        )
    except ValueError as exc:
        # This is raised by build_hotel_report_from_portfolio()
        raise HTTPException(status_code=404, detail=str(exc))

    return hotel_report
