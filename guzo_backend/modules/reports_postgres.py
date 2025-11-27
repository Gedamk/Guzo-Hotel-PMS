# -*- coding: utf-8 -*-
"""
reports_postgres.py – Global-standard room reports from PostgreSQL

Uses bookings + hotels tables to produce:
- Portfolio monthly summary
- Per-hotel monthly summary

KPIs:
- bookings_count
- room_nights_sold
- room_revenue_etb
- ADR (Average Daily Rate)
- RevPAR (Revenue Per Available Room)
- Occupancy % (room_nights_sold / rooms_available)

This is the engine behind:
    GET /reports/portfolio?year=YYYY&month=MM
    GET /reports/hotel/{property_code}?year=YYYY&month=MM
"""

from __future__ import annotations

import calendar
import logging
from datetime import date
from typing import Any, Dict, List, Tuple, Optional

import os  # Reuse same env config style as postgres_bookings.py
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


# ----------------------------------------
# Static room counts per property (for now)
# Later: move this into a hotels/room_inventory table
# ----------------------------------------
ROOMS_TOTAL_BY_PROPERTY: Dict[str, int] = {
    "DRE001": 60,   # Dream Big Hotel
    "N&N002": 45,   # N&N Luxury Hotel
}


# ----------------------------------------
# Connection helper
# ----------------------------------------
def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        raise RuntimeError("GUZO_DB_PASSWORD is not set in environment")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


# ----------------------------------------
# Date helpers
# ----------------------------------------
def get_month_bounds(year: int, month: int) -> Tuple[date, date, int]:
    """
    Return (start_date, end_date, days_in_month) for a given year+month.
    """
    start_date = date(year, month, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    end_date = date(year, month, days_in_month)
    return start_date, end_date, days_in_month


# ----------------------------------------
# Core SQL helpers
# ----------------------------------------
def _fetch_per_hotel_monthly(
    conn,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """
    Return one row per hotel for the given period, with base KPIs from bookings.
    NOTE: We do NOT read rooms_total from DB (column doesn't exist).
          We will inject rooms_total from ROOMS_TOTAL_BY_PROPERTY later.
    """
    sql = """
        SELECT
            b.property_code,
            h.name AS hotel_name,
            COUNT(*) AS bookings_count,
            COALESCE(SUM(b.nights), 0) AS room_nights_sold,
            COALESCE(SUM(b.total_revenue_etb), 0) AS room_revenue_etb
        FROM bookings b
        JOIN hotels h
          ON b.property_code = h.property_code
        WHERE b.check_in_date >= %s
          AND b.check_in_date <= %s
        GROUP BY
            b.property_code,
            h.name
        ORDER BY
            h.name,
            b.property_code;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()
    return rows


def _compute_kpis_for_hotel_row(
    row: Dict[str, Any],
    days_in_month: int,
) -> Dict[str, Any]:
    """
    Take a row with basic sums and add ADR, RevPAR, occupancy, rooms_available.
    Requires row["rooms_total"] to be set by the caller.
    """
    rooms_total = row.get("rooms_total") or 0
    room_nights = float(row.get("room_nights_sold") or 0)
    room_revenue = float(row.get("room_revenue_etb") or 0.0)

    rooms_available = float(rooms_total * days_in_month) if rooms_total else 0.0

    adr = room_revenue / room_nights if room_nights > 0 else 0.0
    revpar = room_revenue / rooms_available if rooms_available > 0 else 0.0
    occupancy_pct = room_nights / rooms_available if rooms_available > 0 else 0.0

    row_out = dict(row)
    row_out.update(
        {
            "rooms_available": rooms_available,
            "adr": round(adr, 2),
            "revpar": round(revpar, 2),
            "occupancy_pct": occupancy_pct,  # raw fraction (0–1)
        }
    )
    return row_out


# ----------------------------------------
# Public API – portfolio + per-hotel reports
# ----------------------------------------
def build_portfolio_report(year: int, month: int) -> Dict[str, Any]:
    """
    Build a global-standard monthly room report for the whole portfolio.
    """
    start_date, end_date, days_in_month = get_month_bounds(year, month)

    try:
        conn = get_connection()
    except Exception as e:
        logger.error("[Reports] ❌ Failed to connect to Postgres: %s", e)
        raise

    try:
        base_rows = _fetch_per_hotel_monthly(conn, start_date, end_date)
    finally:
        conn.close()

    per_hotel: List[Dict[str, Any]] = []
    portfolio_bookings = 0
    portfolio_room_nights = 0.0
    portfolio_room_revenue = 0.0
    portfolio_rooms_total = 0
    portfolio_rooms_available = 0.0

    for row in base_rows:
        property_code = row.get("property_code")
        rooms_total = ROOMS_TOTAL_BY_PROPERTY.get(property_code, 0)
        row["rooms_total"] = rooms_total

        enriched = _compute_kpis_for_hotel_row(row, days_in_month)
        per_hotel.append(enriched)

        portfolio_bookings += int(enriched["bookings_count"])
        portfolio_room_nights += float(enriched["room_nights_sold"])
        portfolio_room_revenue += float(enriched["room_revenue_etb"])
        portfolio_rooms_total += int(enriched.get("rooms_total") or 0)
        portfolio_rooms_available += float(enriched.get("rooms_available") or 0.0)

    # Portfolio-level KPIs
    adr = (
        portfolio_room_revenue / portfolio_room_nights
        if portfolio_room_nights > 0
        else 0.0
    )
    revpar = (
        portfolio_room_revenue / portfolio_rooms_available
        if portfolio_rooms_available > 0
        else 0.0
    )
    occupancy_pct = (
        portfolio_room_nights / portfolio_rooms_available
        if portfolio_rooms_available > 0
        else 0.0
    )

    summary = {
        "bookings_count": portfolio_bookings,
        "room_nights_sold": portfolio_room_nights,
        "room_revenue_etb": portfolio_room_revenue,
        "rooms_total": portfolio_rooms_total,
        "rooms_available": portfolio_rooms_available,
        "adr": round(adr, 2),
        "revpar": round(revpar, 2),
        "occupancy_pct": occupancy_pct,
    }

    report = {
        "scope": "portfolio",
        "year": year,
        "month": month,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "summary": summary,
        "per_hotel": per_hotel,
    }

    return {
        "year": year,
        "month": month,
        "scope": "portfolio",
        "report": report,
    }


def build_hotel_report(
    property_code: str,
    year: int,
    month: int,
) -> Optional[Dict[str, Any]]:
    """
    Build a monthly report for a single hotel.
    JSON shape (similar to portfolio but just one hotel in per_hotel).
    """
    start_date, end_date, days_in_month = get_month_bounds(year, month)

    try:
        conn = get_connection()
    except Exception as e:
        logger.error("[Reports] ❌ Failed to connect to Postgres: %s", e)
        raise

    try:
        sql = """
            SELECT
                b.property_code,
                h.name AS hotel_name,
                COUNT(*) AS bookings_count,
                COALESCE(SUM(b.nights), 0) AS room_nights_sold,
                COALESCE(SUM(b.total_revenue_etb), 0) AS room_revenue_etb
            FROM bookings b
            JOIN hotels h
              ON b.property_code = h.property_code
            WHERE b.check_in_date >= %s
              AND b.check_in_date <= %s
              AND b.property_code = %s
            GROUP BY
                b.property_code,
                h.name
            LIMIT 1;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (start_date, end_date, property_code))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        logger.info(
            "[Reports] No bookings found for property_code=%s in %04d-%02d",
            property_code,
            year,
            month,
        )
        return None

    # Inject rooms_total from static mapping
    rooms_total = ROOMS_TOTAL_BY_PROPERTY.get(row.get("property_code"), 0)
    row["rooms_total"] = rooms_total

    enriched = _compute_kpis_for_hotel_row(row, days_in_month)

    summary = {
        "bookings_count": int(enriched["bookings_count"]),
        "room_nights_sold": float(enriched["room_nights_sold"]),
        "room_revenue_etb": float(enriched["room_revenue_etb"]),
        "rooms_total": int(enriched.get("rooms_total") or 0),
        "rooms_available": float(enriched.get("rooms_available") or 0.0),
        "adr": float(enriched["adr"]),
        "revpar": float(enriched["revpar"]),
        "occupancy_pct": float(enriched["occupancy_pct"]),
    }

    report = {
        "scope": "hotel",
        "year": year,
        "month": month,
        "property_code": property_code,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "summary": summary,
        "per_hotel": [enriched],
    }

    return {
        "year": year,
        "month": month,
        "scope": "hotel",
        "report": report,
    }
