# -*- coding: utf-8 -*-
"""
reports_monthly_owner.py – Monthly Owner / Tax Report (v1.0)
------------------------------------------------------------
Generates PMS-style monthly summary for each hotel:

- Room nights sold
- Room revenue (ETB)
- ADR (Average Daily Rate)
- RevPAR (Revenue per Available Room)
- Occupancy %
- Breakdown by payment method
- Raw booking list (for export / tax / audit)

Data Source: PostgreSQL
  - hotels table
  - bookings table (one row per booking)
"""

import os
import datetime
import logging
from typing import Optional, Dict, Any, List

from guzo_backend.modules.postgres_bookings import get_connection

logger = logging.getLogger(__name__)

# Default rooms_total per property (until you add a column in DB)
# You can tune these values to match each hotel.
DEFAULT_ROOMS_TOTAL = int(os.getenv("DEFAULT_ROOMS_TOTAL", "60"))

PROPERTY_ROOMS_MAP = {
    # Example overrides:
    # "DRE001": 60,
    # "N&N002": 80,
}


def _get_rooms_total(property_code: Optional[str]) -> int:
    """
    Return configured rooms_total for a hotel.
    Uses PROPERTY_ROOMS_MAP first, then DEFAULT_ROOMS_TOTAL.
    """
    if property_code and property_code in PROPERTY_ROOMS_MAP:
        return PROPERTY_ROOMS_MAP[property_code]
    return DEFAULT_ROOMS_TOTAL


def _month_bounds(year: int, month: int) -> (datetime.date, datetime.date):
    """
    Get (start_date, end_date) for the month.
    end_date is exclusive.
    """
    start = datetime.date(year, month, 1)
    # add 32 days then go back to first of next month
    tmp = start + datetime.timedelta(days=32)
    end = tmp.replace(day=1)
    return start, end


def get_monthly_owner_report(
    year: int,
    month: int,
    property_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a monthly summary report.

    Args:
        year: e.g., 2025
        month: 1–12
        property_code: if None, portfolio summary (all hotels);
                       if set, single hotel only.

    Returns:
        {
          "scope": "single" | "portfolio",
          "year": 2025,
          "month": 11,
          "month_label": "2025-11",
          "hotel": {
             "property_code": "...",
             "name": "...",
          } or None,
          "summary": {...},
          "per_hotel": [...],   # only for portfolio mode
          "by_payment_method": [...],
          "bookings": [...],    # raw booking rows
        }
    """
    start, end = _month_bounds(year, month)
    month_label = f"{year:04d}-{month:02d}"

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                params: Dict[str, Any] = {
                    "start": start,
                    "end": end,
                }

                where_clauses = ["b.check_in_date >= %(start)s", "b.check_in_date < %(end)s"]
                if property_code:
                    where_clauses.append("h.property_code = %(property_code)s")
                    params["property_code"] = property_code

                where_sql = " AND ".join(where_clauses)

                # ------------------------------------------------
                # 1) Optional: hotel info (for single-hotel mode)
                # ------------------------------------------------
                hotel_info: Optional[Dict[str, Any]] = None
                if property_code:
                    cur.execute(
                        """
                        SELECT id, property_code, name
                        FROM hotels
                        WHERE property_code = %(property_code)s
                        """,
                        params,
                    )
                    row = cur.fetchone()
                    if row:
                        hotel_info = {
                            "id": row[0],
                            "property_code": row[1],
                            "name": row[2],
                        }

                # ------------------------------------------------
                # 2) Portfolio-level summary (or single hotel if filtered)
                # ------------------------------------------------
                cur.execute(
                    f"""
                    SELECT
                      COUNT(*) AS bookings_count,
                      COALESCE(SUM(b.nights), 0) AS room_nights_sold,
                      COALESCE(SUM(b.total_revenue_etb), 0) AS room_revenue_etb
                    FROM bookings b
                    JOIN hotels h ON b.hotel_id = h.id
                    WHERE {where_sql};
                    """,
                    params,
                )
                row = cur.fetchone()
                if row:
                    bookings_count = int(row[0])
                    room_nights_sold = float(row[1])
                    room_revenue_etb = float(row[2])
                else:
                    bookings_count = 0
                    room_nights_sold = 0.0
                    room_revenue_etb = 0.0

                # Determine rooms_total for occupancy & RevPAR
                rooms_total = _get_rooms_total(property_code)
                days_in_period = (end - start).days
                rooms_available = rooms_total * days_in_period if rooms_total and days_in_period else 0

                if room_nights_sold > 0:
                    adr = room_revenue_etb / room_nights_sold
                else:
                    adr = 0.0

                if rooms_available > 0:
                    revpar = room_revenue_etb / rooms_available
                    occupancy_pct = (room_nights_sold / rooms_available) * 100.0
                else:
                    revpar = 0.0
                    occupancy_pct = 0.0

                summary = {
                    "bookings_count": bookings_count,
                    "room_nights_sold": room_nights_sold,
                    "room_revenue_etb": room_revenue_etb,
                    "rooms_total": rooms_total,
                    "rooms_available": rooms_available,
                    "adr": adr,
                    "revpar": revpar,
                    "occupancy_pct": occupancy_pct,
                }

                # ------------------------------------------------
                # 3) Per-hotel breakdown (for portfolio mode)
                # ------------------------------------------------
                per_hotel: List[Dict[str, Any]] = []
                if not property_code:
                    cur.execute(
                        f"""
                        SELECT
                          h.property_code,
                          h.name,
                          COUNT(*) AS bookings_count,
                          COALESCE(SUM(b.nights), 0) AS room_nights_sold,
                          COALESCE(SUM(b.total_revenue_etb), 0) AS room_revenue_etb
                        FROM bookings b
                        JOIN hotels h ON b.hotel_id = h.id
                        WHERE {where_sql}
                        GROUP BY h.property_code, h.name
                        ORDER BY h.property_code;
                        """,
                        params,
                    )
                    rows = cur.fetchall()
                    for r in rows:
                        pc = r[0]
                        hn = r[1]
                        bk = int(r[2])
                        rn = float(r[3])
                        rev = float(r[4])

                        rooms_total_h = _get_rooms_total(pc)
                        rooms_available_h = rooms_total_h * days_in_period if rooms_total_h and days_in_period else 0
                        adr_h = rev / rn if rn > 0 else 0.0
                        revpar_h = rev / rooms_available_h if rooms_available_h > 0 else 0.0
                        occ_h = (rn / rooms_available_h) * 100.0 if rooms_available_h > 0 else 0.0

                        per_hotel.append(
                            {
                                "property_code": pc,
                                "name": hn,
                                "bookings_count": bk,
                                "room_nights_sold": rn,
                                "room_revenue_etb": rev,
                                "rooms_total": rooms_total_h,
                                "rooms_available": rooms_available_h,
                                "adr": adr_h,
                                "revpar": revpar_h,
                                "occupancy_pct": occ_h,
                            }
                        )

                # ------------------------------------------------
                # 4) Breakdown by payment method
                # ------------------------------------------------
                cur.execute(
                    f"""
                    SELECT
                      b.payment_method,
                      COUNT(*) AS bookings_count,
                      COALESCE(SUM(b.nights), 0) AS room_nights_sold,
                      COALESCE(SUM(b.total_revenue_etb), 0) AS room_revenue_etb
                    FROM bookings b
                    JOIN hotels h ON b.hotel_id = h.id
                    WHERE {where_sql}
                    GROUP BY b.payment_method
                    ORDER BY room_revenue_etb DESC;
                    """,
                    params,
                )
                by_payment_method = []
                for r in cur.fetchall():
                    by_payment_method.append(
                        {
                            "payment_method": r[0] or "Unknown",
                            "bookings_count": int(r[1]),
                            "room_nights_sold": float(r[2]),
                            "room_revenue_etb": float(r[3]),
                        }
                    )

                # ------------------------------------------------
                # 5) Raw bookings (for export / tax / audit)
                # ------------------------------------------------
                cur.execute(
                    f"""
                    SELECT
                      b.confirmation_id,
                      h.property_code,
                      h.name,
                      b.guest_name,
                      b.check_in_date,
                      b.check_out_date,
                      b.nights,
                      b.room_type,
                      b.total_revenue_etb,
                      b.payment_method,
                      b.booking_status,
                      b.payment_status
                    FROM bookings b
                    JOIN hotels h ON b.hotel_id = h.id
                    WHERE {where_sql}
                    ORDER BY h.property_code, b.check_in_date, b.confirmation_id;
                    """,
                    params,
                )
                bookings_rows = []
                for r in cur.fetchall():
                    bookings_rows.append(
                        {
                            "confirmation_id": r[0],
                            "property_code": r[1],
                            "hotel_name": r[2],
                            "guest_name": r[3],
                            "check_in_date": r[4].isoformat() if r[4] else None,
                            "check_out_date": r[5].isoformat() if r[5] else None,
                            "nights": int(r[6]) if r[6] is not None else None,
                            "room_type": r[7],
                            "total_revenue_etb": float(r[8]) if r[8] is not None else 0.0,
                            "payment_method": r[9],
                            "booking_status": r[10],
                            "payment_status": r[11],
                        }
                    )

        scope = "single" if property_code else "portfolio"

        result: Dict[str, Any] = {
            "scope": scope,
            "year": year,
            "month": month,
            "month_label": month_label,
            "hotel": None,
            "summary": summary,
            "per_hotel": per_hotel,
            "by_payment_method": by_payment_method,
            "bookings": bookings_rows,
        }

        if hotel_info:
            result["hotel"] = {
                "property_code": hotel_info["property_code"],
                "name": hotel_info["name"],
            }

        logger.info(
            "[MonthlyOwner] Generated %s report for %s (property_code=%s): %s",
            scope,
            month_label,
            property_code,
            summary,
        )

        return result

    finally:
        conn.close()


# ==========================================================
# SELF-TEST (run directly)
# ==========================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    today = datetime.date.today()
    year = today.year
    month = today.month

    example_property_code = os.getenv("EXAMPLE_PROPERTY_CODE", "DRE001")

    print("🧪 Monthly Owner Report – self-test")
    print(f"Month: {year}-{month:02d}, property_code={example_property_code}")

    report = get_monthly_owner_report(year, month, property_code=example_property_code)

    print("\n=== SUMMARY ===")
    print(f"Scope: {report['scope']}")
    print(f"Month: {report['month_label']}")
    print("Hotel:", report.get("hotel"))
    for k, v in report["summary"].items():
        print(f" - {k}: {v}")

    print("\n=== By Payment Method ===")
    for row in report["by_payment_method"]:
        print(
            f"{row['payment_method']}: {row['bookings_count']} bookings, "
            f"{row['room_nights_sold']} nights, ETB {row['room_revenue_etb']}"
        )

    print("\n=== Example Bookings (first 5) ===")
    for row in report["bookings"][:5]:
        print(
            f"{row['confirmation_id']} | {row['property_code']} | "
            f"{row['guest_name']} | {row['check_in_date']} -> {row['check_out_date']} | "
            f"ETB {row['total_revenue_etb']} | {row['payment_method']}"
        )

    print("\n✅ Monthly Owner self-test finished.")
