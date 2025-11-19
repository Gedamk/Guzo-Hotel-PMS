# -*- coding: utf-8 -*-
"""
reports_portfolio_owner.py – Portfolio / Group Owner Analytics (v1.0)
---------------------------------------------------------------------
Aggregates performance across ALL hotels in the portfolio using Postgres.

Designed for:
- Hotel groups
- Multi-property Airbnb / lodge owners
- Regional managers and investors

Metrics:
- Portfolio totals (room nights, revenue, ADR, RevPAR, Occupancy)
- Per-hotel KPIs
- Payment-method breakdown
- Daily revenue trend for charts

Best practice:
- Uses Postgres as single source of truth
- Keeps business logic in backend (this module)
- Streamlit dashboard only does visualization
"""

import os
import datetime
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

from dotenv import load_dotenv
from guzo_backend.modules.postgres_bookings import get_connection

# 🔑 Load .env so GUZO_DB_* variables are available
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------
def _daterange(start: datetime.date, end: datetime.date):
    """Yield each date from start to end (inclusive)."""
    delta = (end - start).days
    for i in range(delta + 1):
        yield start + datetime.timedelta(days=i)


def _get_month_bounds(year: int, month: int):
    """Return (start_date, end_date) for a given year/month."""
    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    return start, end


# -------------------------------------------------------------------
# Core report function
# -------------------------------------------------------------------
def get_portfolio_owner_report(
    year: int,
    month: Optional[int] = None,
    property_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Aggregate KPIs across all hotels in the portfolio.

    Params
    ------
    year: int
        Calendar year for the report.
    month: Optional[int]
        If provided (1–12), limits data to that month only.
        If None, aggregates over the full year.
    property_codes: Optional[List[str]]
        If provided, restricts to these property_code values.
        If None, includes all hotels.

    Returns
    -------
    Dict[str, Any] with keys:
        scope: "portfolio"
        year, month
        period: {"start_date", "end_date"}
        summary: {
            bookings_count, room_nights_sold, room_revenue_etb,
            rooms_total, rooms_available, adr, revpar, occupancy_pct
        }
        per_hotel: List[{
            property_code, hotel_name,
            bookings_count, room_nights_sold, room_revenue_etb,
            rooms_total, rooms_available, adr, revpar, occupancy_pct
        }]
        by_payment_method: List[{
            payment_method, bookings_count, nights, revenue_etb
        }]
        daily_trend: List[{
            date, room_revenue_etb, room_nights
        }]
        sample_bookings: first few booking rows for debugging.
    """
    logger.info(
        "[PortfolioOwner] Generating portfolio report for %s-%s (properties=%s)",
        year,
        month or "ALL",
        property_codes or "ALL",
    )

    if month:
        start_date, end_date = _get_month_bounds(year, month)
    else:
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Build WHERE conditions
                where_clauses = [
                    "b.check_in_date <= %(end_date)s",
                    "b.check_out_date >= %(start_date)s",
                    "b.booking_status = 'Confirmed'",
                ]
                params: Dict[str, Any] = {
                    "start_date": start_date,
                    "end_date": end_date,
                }

                if property_codes:
                    where_clauses.append("h.property_code = ANY(%(property_codes)s)")
                    params["property_codes"] = property_codes

                where_sql = " AND ".join(where_clauses)

                sql = f"""
                    SELECT
                        h.id AS hotel_id,
                        h.property_code,
                        h.name AS hotel_name,
                        b.id AS booking_id,
                        b.confirmation_id,
                        b.check_in_date,
                        b.check_out_date,
                        b.nights,
                        b.total_revenue_etb,
                        b.payment_method
                    FROM bookings b
                    JOIN hotels h ON b.hotel_id = h.id
                    WHERE {where_sql}
                """

                cur.execute(sql, params)
                rows = cur.fetchall()

                col_names = [desc[0] for desc in cur.description]
                bookings: List[Dict[str, Any]] = []
                for r in rows:
                    item = dict(zip(col_names, r))
                    bookings.append(item)

        # If no bookings, still return a valid empty structure
        if not bookings:
            logger.info("[PortfolioOwner] No bookings found for the selected period.")
            return {
                "scope": "portfolio",
                "year": year,
                "month": month,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "bookings_count": 0,
                    "room_nights_sold": 0.0,
                    "room_revenue_etb": 0.0,
                    "rooms_total": 0,
                    "rooms_available": 0,
                    "adr": 0.0,
                    "revpar": 0.0,
                    "occupancy_pct": 0.0,
                },
                "per_hotel": [],
                "by_payment_method": [],
                "daily_trend": [],
                "sample_bookings": [],
            }

        # ------------------------------------------------------------------
        # Aggregations
        # ------------------------------------------------------------------
        per_hotel_stats: Dict[str, Dict[str, Any]] = {}
        payment_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"bookings_count": 0, "nights": 0.0, "revenue_etb": 0.0}
        )
        daily_trend: Dict[datetime.date, Dict[str, float]] = defaultdict(
            lambda: {"room_revenue_etb": 0.0, "room_nights": 0.0}
        )

        # For now, assume default rooms per hotel (later you can
        # extend the hotels table with rooms_total and read from there)
        DEFAULT_ROOMS_PER_HOTEL = 60

        for b in bookings:
            pc = b["property_code"]
            hotel_name = b["hotel_name"]
            nights = float(b["nights"] or 0)
            revenue = float(b["total_revenue_etb"] or 0)
            payment_method = b["payment_method"] or "Unknown"
            check_in: datetime.date = b["check_in_date"]
            check_out: datetime.date = b["check_out_date"]

            # Initialize per-hotel struct
            if pc not in per_hotel_stats:
                per_hotel_stats[pc] = {
                    "property_code": pc,
                    "hotel_name": hotel_name,
                    "bookings_count": 0,
                    "room_nights_sold": 0.0,
                    "room_revenue_etb": 0.0,
                    "rooms_total": DEFAULT_ROOMS_PER_HOTEL,
                }

            hstats = per_hotel_stats[pc]
            hstats["bookings_count"] += 1
            hstats["room_nights_sold"] += nights
            hstats["room_revenue_etb"] += revenue

            # Payment aggregation
            pst = payment_stats[payment_method]
            pst["bookings_count"] += 1
            pst["nights"] += nights
            pst["revenue_etb"] += revenue

            # Daily trend – spread revenue and nights evenly across stay
            stay_nights = max((check_out - check_in).days, 1)
            if stay_nights <= 0:
                stay_nights = 1
            per_night_rev = revenue / stay_nights if revenue else 0.0

            for dt in _daterange(
                max(check_in, start_date),
                min(check_out - datetime.timedelta(days=1), end_date),
            ):
                dtr = daily_trend[dt]
                dtr["room_revenue_etb"] += per_night_rev
                dtr["room_nights"] += 1.0

        # Compute per-hotel ADR / RevPAR / Occupancy
        total_bookings = 0
        total_nights = 0.0
        total_revenue = 0.0
        total_rooms_available = 0

        total_days = (end_date - start_date).days + 1

        for h in per_hotel_stats.values():
            rooms_total = h["rooms_total"]
            rooms_available = rooms_total * total_days
            h["rooms_available"] = rooms_available

            nights_sold = h["room_nights_sold"]
            revenue = h["room_revenue_etb"]

            h["adr"] = revenue / nights_sold if nights_sold > 0 else 0.0
            h["revpar"] = revenue / rooms_available if rooms_available > 0 else 0.0
            h["occupancy_pct"] = (
                100.0 * nights_sold / rooms_available if rooms_available > 0 else 0.0
            )

            # portfolio totals
            total_bookings += h["bookings_count"]
            total_nights += nights_sold
            total_revenue += revenue
            total_rooms_available += rooms_available

        portfolio_adr = total_revenue / total_nights if total_nights > 0 else 0.0
        portfolio_revpar = (
            total_revenue / total_rooms_available if total_rooms_available > 0 else 0.0
        )
        portfolio_occ = (
            100.0 * total_nights / total_rooms_available
            if total_rooms_available > 0
            else 0.0
        )

        # Prepare output structures
        per_hotel_list = sorted(
            per_hotel_stats.values(),
            key=lambda x: x["room_revenue_etb"],
            reverse=True,
        )

        by_payment_list = [
            {
                "payment_method": pm,
                "bookings_count": v["bookings_count"],
                "nights": v["nights"],
                "revenue_etb": v["revenue_etb"],
            }
            for pm, v in payment_stats.items()
        ]
        by_payment_list.sort(key=lambda x: x["revenue_etb"], reverse=True)

        daily_trend_list = [
            {
                "date": d.isoformat(),
                "room_revenue_etb": vals["room_revenue_etb"],
                "room_nights": vals["room_nights"],
            }
            for d, vals in sorted(daily_trend.items(), key=lambda kv: kv[0])
        ]

        # Small sample of bookings for debugging
        sample_bookings = []
        for b in bookings[:10]:
            sample_bookings.append(
                {
                    "confirmation_id": b["confirmation_id"],
                    "property_code": b["property_code"],
                    "hotel_name": b["hotel_name"],
                    "check_in_date": b["check_in_date"].isoformat(),
                    "check_out_date": b["check_out_date"].isoformat(),
                    "nights": float(b["nights"] or 0),
                    "revenue_etb": float(b["total_revenue_etb"] or 0),
                    "payment_method": b["payment_method"] or "Unknown",
                }
            )

        summary = {
            "bookings_count": total_bookings,
            "room_nights_sold": total_nights,
            "room_revenue_etb": total_revenue,
            "rooms_total": sum(h["rooms_total"] for h in per_hotel_list),
            "rooms_available": total_rooms_available,
            "adr": portfolio_adr,
            "revpar": portfolio_revpar,
            "occupancy_pct": portfolio_occ,
        }

        logger.info(
            "[PortfolioOwner] Portfolio summary: %s",
            summary,
        )

        return {
            "scope": "portfolio",
            "year": year,
            "month": month,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": summary,
            "per_hotel": per_hotel_list,
            "by_payment_method": by_payment_list,
            "daily_trend": daily_trend_list,
            "sample_bookings": sample_bookings,
        }

    finally:
        conn.close()


# -------------------------------------------------------------------
# Self-test
# -------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    today = datetime.date.today()
    year = today.year
    month = today.month

    print("🧪 Portfolio Owner Report – self-test")
    print(f"Period: {year}-{month:02d} (all properties)")
    report = get_portfolio_owner_report(year, month)

    print("\n=== SUMMARY ===")
    for k, v in report["summary"].items():
        print(f" - {k}: {v}")

    print("\n=== Per Hotel (top 5) ===")
    for h in report["per_hotel"][:5]:
        print(
            f"{h['property_code']} | {h['hotel_name']} | Rev: {h['room_revenue_etb']} | "
            f"Occ: {h['occupancy_pct']:.2f}% | ADR: {h['adr']:.2f} | RevPAR: {h['revpar']:.2f}"
        )

    print("\n✅ Portfolio Owner self-test finished.")
