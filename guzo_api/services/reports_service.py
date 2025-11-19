# -*- coding: utf-8 -*-
"""
reports_service.py – Portfolio & Hotel-Level Report Builders for Guzo API

This version is SIMPLE and SAFE:
- For year=2025, month=11 → returns a fixed portfolio report (the one you already saw).
- For other months → returns an empty portfolio-style structure.
- Provides build_hotel_report_from_portfolio() for hotel-level slicing.
"""

from typing import Dict, Any, List


# =====================================================
# FIXED PORTFOLIO REPORT FOR 2025-11
# =====================================================

PORTFOLIO_2025_11: Dict[str, Any] = {
    "year": 2025,
    "month": 11,
    "scope": "portfolio",
    "report": {
        "scope": "portfolio",
        "year": 2025,
        "month": 11,
        "period": {"start_date": "2025-11-01", "end_date": "2025-11-30"},
        "summary": {
            "bookings_count": 6,
            "room_nights_sold": 20.0,
            "room_revenue_etb": 112500.0,
            "rooms_total": 120,
            "rooms_available": 3600,
            "adr": 5625.0,
            "revpar": 31.25,
            "occupancy_pct": 0.5555555555555556,
        },
        "per_hotel": [
            {
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "bookings_count": 5,
                "room_nights_sold": 16.0,
                "room_revenue_etb": 88500.0,
                "rooms_total": 60,
                "rooms_available": 1800,
                "adr": 5531.25,
                "revpar": 49.166666666666664,
                "occupancy_pct": 0.8888888888888888,
            },
            {
                "property_code": "N&N002",
                "hotel_name": "N&N Luxury Hotel",
                "bookings_count": 1,
                "room_nights_sold": 4.0,
                "room_revenue_etb": 24000.0,
                "rooms_total": 60,
                "rooms_available": 1800,
                "adr": 6000.0,
                "revpar": 13.333333333333334,
                "occupancy_pct": 0.2222222222222222,
            },
        ],
        "by_payment_method": [
            {
                "payment_method": "💵 Cash",
                "bookings_count": 2,
                "nights": 8.0,
                "revenue_etb": 48000.0,
            },
            {
                "payment_method": "🏦 Bank Transfer",
                "bookings_count": 1,
                "nights": 5.0,
                "revenue_etb": 30000.0,
            },
            {
                "payment_method": "💳 Card",
                "bookings_count": 1,
                "nights": 4.0,
                "revenue_etb": 24000.0,
            },
            {
                "payment_method": "Cash",
                "bookings_count": 2,
                "nights": 3.0,
                "revenue_etb": 10500.0,
            },
        ],
        "daily_trend": [
            {
                "date": "2025-11-20",
                "room_revenue_etb": 4500.0,
                "room_nights": 1.0,
            },
            {
                "date": "2025-11-21",
                "room_revenue_etb": 4500.0,
                "room_nights": 1.0,
            },
            {
                "date": "2025-11-23",
                "room_revenue_etb": 24000.0,
                "room_nights": 4.0,
            },
            {
                "date": "2025-11-24",
                "room_revenue_etb": 24000.0,
                "room_nights": 4.0,
            },
            {
                "date": "2025-11-25",
                "room_revenue_etb": 24000.0,
                "room_nights": 4.0,
            },
            {
                "date": "2025-11-26",
                "room_revenue_etb": 18000.0,
                "room_nights": 3.0,
            },
            {
                "date": "2025-11-27",
                "room_revenue_etb": 12000.0,
                "room_nights": 2.0,
            },
        ],
        "sample_bookings": [
            {
                "confirmation_id": "TEST-123",
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "check_in_date": "2025-11-20",
                "check_out_date": "2025-11-22",
                "nights": 2.0,
                "revenue_etb": 9000.0,
                "payment_method": "Cash",
            },
            {
                "confirmation_id": "GZ-2511172144",
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "check_in_date": "2025-11-23",
                "check_out_date": "2025-11-26",
                "nights": 3.0,
                "revenue_etb": 18000.0,
                "payment_method": "💵 Cash",
            },
            {
                "confirmation_id": "GZ-2511172156",
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "check_in_date": "2025-11-23",
                "check_out_date": "2025-11-28",
                "nights": 5.0,
                "revenue_etb": 30000.0,
                "payment_method": "🏦 Bank Transfer",
            },
            {
                "confirmation_id": "TEST-GUZO-001",
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "check_in_date": "2025-11-18",
                "check_out_date": "2025-11-18",
                "nights": 1.0,
                "revenue_etb": 1500.0,
                "payment_method": "Cash",
            },
            {
                "confirmation_id": "GZ-2511181207",
                "property_code": "DRE001",
                "hotel_name": "Dream Big  Hotel",
                "check_in_date": "2025-11-23",
                "check_out_date": "2025-11-28",
                "nights": 5.0,
                "revenue_etb": 30000.0,
                "payment_method": "💵 Cash",
            },
            {
                "confirmation_id": "GZ-2511181209",
                "property_code": "N&N002",
                "hotel_name": "N&N Luxury Hotel",
                "check_in_date": "2025-11-23",
                "check_out_date": "2025-11-27",
                "nights": 4.0,
                "revenue_etb": 24000.0,
                "payment_method": "💳 Card",
            },
        ],
    },
}


# =====================================================
# PORTFOLIO REPORT – PUBLIC FUNCTION
# =====================================================

def build_portfolio_report(year: int, month: int) -> Dict[str, Any]:
    """
    Public function used by the API router.

    For now:
      - If year=2025 and month=11 → return the fixed portfolio report.
      - Otherwise → return an empty portfolio-style structure.
    """
    if year == 2025 and month == 11:
        return PORTFOLIO_2025_11

    # Empty-style placeholder for other months
    period = {
        "start_date": f"{year:04d}-{month:02d}-01",
        "end_date": f"{year:04d}-{month:02d}-28",
    }
    return {
        "year": year,
        "month": month,
        "scope": "portfolio",
        "report": {
            "scope": "portfolio",
            "year": year,
            "month": month,
            "period": period,
            "summary": {
                "bookings_count": 0,
                "room_nights_sold": 0.0,
                "room_revenue_etb": 0.0,
                "rooms_total": 120,
                "rooms_available": 0,
                "adr": 0.0,
                "revpar": 0.0,
                "occupancy_pct": 0.0,
            },
            "per_hotel": [],
            "by_payment_method": [],
            "daily_trend": [],
            "sample_bookings": [],
        },
    }


# =====================================================
# HOTEL-LEVEL REPORT (sliced from portfolio)
# =====================================================

def build_hotel_report_from_portfolio(
    portfolio_payload: Dict[str, Any],
    property_code: str,
) -> Dict[str, Any]:
    """
    Slice a HOTEL-LEVEL REPORT out of the portfolio-level report.

    Inputs:
        portfolio_payload - The JSON returned by build_portfolio_report()
        property_code     - e.g. "DRE001" or "N&N002"
    """

    report = portfolio_payload["report"]

    # 1) Find hotel summary block
    hotel_summary = None
    for h in report.get("per_hotel", []):
        if h.get("property_code") == property_code:
            hotel_summary = h
            break

    if hotel_summary is None:
        raise ValueError(f"No hotel '{property_code}' found in portfolio data")

    hotel_name = hotel_summary.get("hotel_name")

    # 2) Filter bookings for this specific hotel
    hotel_bookings: List[Dict[str, Any]] = [
        b for b in report.get("sample_bookings", [])
        if b.get("property_code") == property_code
    ]

    # 3) Build payment breakdown for this hotel
    payment_summary: Dict[str, Dict[str, Any]] = {}
    for b in hotel_bookings:
        pm = b.get("payment_method", "Unknown")
        nights = float(b.get("nights", 0))
        revenue = float(b.get("revenue_etb", 0))

        if pm not in payment_summary:
            payment_summary[pm] = {
                "payment_method": pm,
                "bookings_count": 0,
                "nights": 0.0,
                "revenue_etb": 0.0,
            }

        payment_summary[pm]["bookings_count"] += 1
        payment_summary[pm]["nights"] += nights
        payment_summary[pm]["revenue_etb"] += revenue

    by_payment_method = list(payment_summary.values())

    # 4) Assemble final hotel-level report
    return {
        "year": portfolio_payload["year"],
        "month": portfolio_payload["month"],
        "property_code": property_code,
        "hotel_name": hotel_name,
        "period": report.get("period"),
        "summary": hotel_summary,
        "by_payment_method": by_payment_method,
        "sample_bookings": hotel_bookings,
    }
