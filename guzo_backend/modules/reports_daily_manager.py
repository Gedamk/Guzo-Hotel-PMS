# -*- coding: utf-8 -*-
"""
reports_daily_manager.py – Daily Manager / GM Report (v1.0)
-----------------------------------------------------------
Generates a PMS-style "Daily Manager Report" per hotel from Postgres.

Uses data from the `bookings` table (and `hotels` for names) to compute:
- Occupancy (approximate, if TOTAL_ROOMS_* env vars are set)
- Room revenue for the day
- ADR (Average Daily Rate)
- RevPAR (Revenue per Available Room)
- Arrivals, Departures, In-House counts
- Detail lists for Arrivals, Departures, In-House

This is the backbone for your Manager Dashboard UI.
"""

import os
import datetime
import logging
from typing import Any, Dict, List, Optional

from guzo_backend.modules.postgres_bookings import get_connection
# Load environment (DB credentials, TOTAL_ROOMS variables, etc.)
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _parse_date(report_date: Any) -> datetime.date:
    """
    Accepts a date, datetime, or 'YYYY-MM-DD' string and
    returns a datetime.date.
    """
    if isinstance(report_date, datetime.date) and not isinstance(report_date, datetime.datetime):
        return report_date
    if isinstance(report_date, datetime.datetime):
        return report_date.date()
    if isinstance(report_date, str):
        return datetime.datetime.strptime(report_date, "%Y-%m-%d").date()
    raise ValueError(f"Unsupported date type: {type(report_date)}")


def _get_total_rooms(property_code: Optional[str]) -> Optional[int]:
    """
    Read TOTAL_ROOMS from environment.

    Strategy:
    - If property_code is provided, try: TOTAL_ROOMS_<PROPERTY_CODE>
      e.g. TOTAL_ROOMS_DRE001=60
    - Fallback to TOTAL_ROOMS_DEFAULT

    If nothing found, return None (report will still work but Occ%/RevPAR
    will be None).
    """
    if property_code:
        key = f"TOTAL_ROOMS_{property_code.upper()}"
        val = os.getenv(key)
        if val:
            try:
                return int(val)
            except ValueError:
                logger.warning(
                    "[DailyManager] Invalid TOTAL_ROOMS value for %s = %r",
                    key,
                    val,
                )

    default_val = os.getenv("TOTAL_ROOMS_DEFAULT")
    if default_val:
        try:
            return int(default_val)
        except ValueError:
            logger.warning(
                "[DailyManager] Invalid TOTAL_ROOMS_DEFAULT value = %r",
                default_val,
            )
    return None


# -----------------------------------------------------------
# Core report function
# -----------------------------------------------------------
def get_daily_manager_report(
    report_date: Any,
    property_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Daily Manager / GM report for a given date and (optional) hotel.

    - report_date: date, datetime, or 'YYYY-MM-DD' string
    - property_code: like 'DRE001', 'N&N002', or None for "all properties"

    Returns a dict:

    {
      "date": "2025-11-18",
      "hotel": {
        "scope": "single" or "all",
        "property_code": "DRE001",
        "name": "Dream Big Hotel",
      },
      "kpis": {
        "rooms_total": 60 or None,
        "rooms_in_house": 25,
        "occupancy_pct": 41.67 or None,
        "room_revenue_etb": 30000.0,
        "adr": 6000.0,
        "revpar": 500.0 or None,
        "arrivals": 5,
        "departures": 3,
        "in_house": 25,
      },
      "arrivals": [ {...}, ... ],
      "departures": [ {...}, ... ],
      "in_house_list": [ {...}, ... ],
    }

    Notes on logic (simple, but PMS-like):
    - Arrivals: bookings with check_in_date = report_date
    - Departures: bookings with check_out_date = report_date
    - In-House: check_in_date <= report_date < check_out_date
    - Revenue for the day: sum(total_revenue_etb) for bookings
      with check_in_date = report_date AND booking_status='Confirmed'
      (this is "arrival-based" revenue; good as a first version)
    """
    target_date = _parse_date(report_date)

    params: Dict[str, Any] = {"report_date": target_date}
    hotel_filter_sql = ""
    hotel_scope_info: Dict[str, Any] = {
        "scope": "all",
        "property_code": None,
        "name": "All Properties",
    }

    if property_code:
        hotel_filter_sql = """
            AND hotel_id = (
                SELECT id FROM hotels WHERE property_code = %(property_code)s
            )
        """
        params["property_code"] = property_code
        hotel_scope_info["scope"] = "single"
        hotel_scope_info["property_code"] = property_code

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # ----------------------------------------
                # Resolve hotel name (if single property)
                # ----------------------------------------
                if property_code:
                    cur.execute(
                        """
                        SELECT name
                        FROM hotels
                        WHERE property_code = %(property_code)s
                        """,
                        params,
                    )
                    row = cur.fetchone()
                    if row:
                        hotel_scope_info["name"] = row[0]
                    else:
                        hotel_scope_info["name"] = f"Unknown ({property_code})"

                # ----------------------------------------
                # Count arrivals, departures, in-house
                # ----------------------------------------
                # Arrivals
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM bookings
                    WHERE booking_status = 'Confirmed'
                      AND check_in_date = %(report_date)s
                      {hotel_filter_sql}
                    """,
                    params,
                )
                arrivals_count = cur.fetchone()[0] or 0

                # Departures
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM bookings
                    WHERE booking_status = 'Confirmed'
                      AND check_out_date = %(report_date)s
                      {hotel_filter_sql}
                    """,
                    params,
                )
                departures_count = cur.fetchone()[0] or 0

                # In-house (guests staying tonight)
                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM bookings
                    WHERE booking_status = 'Confirmed'
                      AND check_in_date <= %(report_date)s
                      AND check_out_date > %(report_date)s
                      {hotel_filter_sql}
                    """,
                    params,
                )
                in_house_count = cur.fetchone()[0] or 0

                # ----------------------------------------
                # Revenue, ADR for arrivals of the day
                # ----------------------------------------
                cur.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(total_revenue_etb), 0.0) AS revenue,
                        COUNT(*) AS num_arrivals
                    FROM bookings
                    WHERE booking_status = 'Confirmed'
                      AND check_in_date = %(report_date)s
                      {hotel_filter_sql}
                    """,
                    params,
                )
                rev_row = cur.fetchone()
                room_revenue_etb = float(rev_row[0] or 0.0)
                num_arrival_bookings = int(rev_row[1] or 0)

                # ADR: revenue / number_of_arrival_bookings (simple version)
                adr = None
                if num_arrival_bookings > 0:
                    adr = room_revenue_etb / num_arrival_bookings

                # ----------------------------------------
                # Occupancy / RevPAR (if TOTAL_ROOMS known)
                # ----------------------------------------
                total_rooms = _get_total_rooms(property_code)
                occupancy_pct = None
                revpar = None
                if total_rooms and total_rooms > 0:
                    occupancy_pct = (in_house_count / float(total_rooms)) * 100.0
                    revpar = room_revenue_etb / float(total_rooms)

                # ----------------------------------------
                # Detail lists
                # ----------------------------------------
                def _fetch_detail_list(condition_sql: str) -> List[Dict[str, Any]]:
                    cur.execute(
                        f"""
                        SELECT
                            confirmation_id,
                            guest_name,
                            guest_email,
                            check_in_date,
                            check_out_date,
                            nights,
                            room_type,
                            total_revenue_etb,
                            payment_method,
                            payment_status,
                            booking_status
                        FROM bookings
                        WHERE booking_status = 'Confirmed'
                          {condition_sql}
                          {hotel_filter_sql}
                        ORDER BY check_in_date, confirmation_id
                        """,
                        params,
                    )
                    rows = cur.fetchall()
                    results: List[Dict[str, Any]] = []
                    for r in rows:
                        results.append(
                            {
                                "confirmation_id": r[0],
                                "guest_name": r[1],
                                "guest_email": r[2],
                                "check_in_date": r[3].isoformat() if r[3] else None,
                                "check_out_date": r[4].isoformat() if r[4] else None,
                                "nights": r[5],
                                "room_type": r[6],
                                "total_revenue_etb": float(r[7]) if r[7] is not None else 0.0,
                                "payment_method": r[8],
                                "payment_status": r[9],
                                "booking_status": r[10],
                            }
                        )
                    return results

                arrivals_list = _fetch_detail_list(
                    "AND check_in_date = %(report_date)s"
                )
                departures_list = _fetch_detail_list(
                    "AND check_out_date = %(report_date)s"
                )
                in_house_list = _fetch_detail_list(
                    "AND check_in_date <= %(report_date)s AND check_out_date > %(report_date)s"
                )

        # Build final payload
        report: Dict[str, Any] = {
            "date": target_date.isoformat(),
            "hotel": hotel_scope_info,
            "kpis": {
                "rooms_total": total_rooms,
                "rooms_in_house": in_house_count,
                "occupancy_pct": occupancy_pct,
                "room_revenue_etb": room_revenue_etb,
                "adr": adr,
                "revpar": revpar,
                "arrivals": arrivals_count,
                "departures": departures_count,
                "in_house": in_house_count,
            },
            "arrivals": arrivals_list,
            "departures": departures_list,
            "in_house_list": in_house_list,
        }

        logger.info(
            "[DailyManager] Generated report for date=%s, property_code=%s: %s",
            report["date"],
            property_code,
            report["kpis"],
        )
        return report

    finally:
        conn.close()


# -----------------------------------------------------------
# Self-test (run manually)
# -----------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    today = datetime.date.today()
    print("🧪 Daily Manager Report – self-test")
    print("Date:", today.isoformat())

    # Example: specific hotel (you can change to 'N&N002', etc.)
    example_property_code = os.getenv("DAILY_MANAGER_TEST_PROPERTY", "DRE001")

    report = get_daily_manager_report(today, property_code=example_property_code)
    print("\n=== SUMMARY ===")
    print("Hotel:", report["hotel"])
    for k, v in report["kpis"].items():
        print(f" - {k}: {v}")

    print("\n=== Arrivals ===")
    for row in report["arrivals"]:
        print(
            f"{row['confirmation_id']} | {row['guest_name']} | "
            f"{row['room_type']} | {row['nights']} nights | ETB {row['total_revenue_etb']}"
        )

    print("\n=== Departures ===")
    for row in report["departures"]:
        print(
            f"{row['confirmation_id']} | {row['guest_name']} | "
            f"{row['room_type']} | out {row['check_out_date']}"
        )

    print("\n=== In-House ===")
    for row in report["in_house_list"]:
        print(
            f"{row['confirmation_id']} | {row['guest_name']} | "
            f"{row['check_in_date']} → {row['check_out_date']} | {row['room_type']}"
        )

    print("\n✅ Daily Manager self-test finished.")
