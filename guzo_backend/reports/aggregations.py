# guzo_backend/reports/aggregations.py
"""
aggregations.py – aggregate bookings into hotel_daily_kpi (Daily KPI Snapshot)

Global PMS "safe" behavior for your current schema:
- Inventory source: housekeeping_status (distinct room_number per property_code)
- Occupancy (rooms_sold): counts DISTINCT occupied room_number on business_date for in-house stays
- Rooms On Books (rooms_on_books): counts DISTINCT assigned room_number on business_date for (in_house + confirmed)
- Bookings On Books (bookings_on_books): counts bookings on business_date for (in_house + confirmed) (room may be NULL)
- Caps rooms_sold to rooms_total (prevents >100% occupancy from bad demo data)
- Revenue: uses bookings.total_amount when available, else nightly_rate * nights, else 0
- Supports CLI usage and nightly scheduler usage
- Auto-loads env from .env.local / .env (never commit real passwords)

Required tables:
- bookings(property_code, room_number, check_in_date, check_out_date, booking_status, total_amount?, nightly_rate?, nights?)
- hotels(property_code, hotel_name?)
- housekeeping_status(property_code, room_number, ...)

Target table:
- hotel_daily_kpi(property_code, hotel_name, business_date, rooms_total, rooms_sold, rooms_available,
                 rooms_on_books, bookings_on_books,
                 room_revenue, adr, revpar, occupancy_pct, fnb_revenue?, other_revenue?, total_revenue?, ...)
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from typing import Dict, List, Optional, Sequence

from psycopg2.extras import DictCursor

from guzo_backend.db import get_connection


# -----------------------------
# Env loading (safe)
# -----------------------------
def _load_env_files() -> None:
    """
    Loads env vars from .env.local then .env if present.
    Works even if python-dotenv is not installed (it will just skip).
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(root, ".env.local"), override=False)
    load_dotenv(os.path.join(root, ".env"), override=False)


def _table_columns(cur: DictCursor, table: str) -> List[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        [table],
    )
    return [r["column_name"] for r in cur.fetchall()]


def _safe_float(x) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _safe_int(x) -> int:
    try:
        if x is None:
            return 0
        return int(x)
    except Exception:
        return 0


# -----------------------------
# Core aggregation
# -----------------------------
def aggregate_day(
    business_date: date,
    property_code: str = "all",
) -> int:
    """
    Aggregates one business date into hotel_daily_kpi.

    Returns: number of rows upserted.
    """
    _load_env_files()

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # ---- Read hotel list
            if property_code == "all":
                cur.execute(
                    """
                    SELECT h.property_code,
                           COALESCE(h.hotel_name, h.property_code) AS hotel_name
                    FROM hotels h
                    ORDER BY h.property_code
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT h.property_code,
                           COALESCE(h.hotel_name, h.property_code) AS hotel_name
                    FROM hotels h
                    WHERE h.property_code = %s
                    """,
                    [property_code],
                )
            hotels = cur.fetchall()
            if not hotels:
                return 0

            # ---- Inventory: housekeeping_status distinct room_number
            inventory_sql = """
                SELECT property_code, COUNT(DISTINCT room_number) AS rooms_total
                FROM housekeeping_status
                WHERE room_number IS NOT NULL AND btrim(room_number) <> ''
                GROUP BY property_code
            """
            cur.execute(inventory_sql)
            inv_map: Dict[str, int] = {
                r["property_code"]: _safe_int(r["rooms_total"]) for r in cur.fetchall()
            }

            # ---- Occupancy: DISTINCT in-house room_number for business_date
            # Global standard: in-house = check_in_date <= biz < check_out_date AND booking_status='in_house'
            occupied_sql = """
                SELECT
                    property_code,
                    COUNT(DISTINCT room_number) AS rooms_occupied
                FROM bookings
                WHERE check_in_date <= %s
                  AND check_out_date > %s
                  AND booking_status = 'in_house'
                  AND room_number IS NOT NULL
                  AND btrim(room_number) <> ''
                GROUP BY property_code
            """
            cur.execute(occupied_sql, [business_date, business_date])
            occ_map: Dict[str, int] = {
                r["property_code"]: _safe_int(r["rooms_occupied"]) for r in cur.fetchall()
            }

            # ---- Rooms On Books: DISTINCT assigned rooms for (in_house + confirmed) staying over biz date
            rooms_on_books_sql = """
                SELECT
                    property_code,
                    COUNT(DISTINCT room_number) AS rooms_on_books
                FROM bookings
                WHERE check_in_date <= %s
                  AND check_out_date > %s
                  AND booking_status IN ('in_house','confirmed')
                  AND room_number IS NOT NULL
                  AND btrim(room_number) <> ''
                GROUP BY property_code
            """
            cur.execute(rooms_on_books_sql, [business_date, business_date])
            rob_map: Dict[str, int] = {
                r["property_code"]: _safe_int(r["rooms_on_books"]) for r in cur.fetchall()
            }

            # ---- Bookings On Books: count bookings for (in_house + confirmed) staying over biz date (room may be NULL)
            bookings_on_books_sql = """
                SELECT
                    property_code,
                    COUNT(*) AS bookings_on_books
                FROM bookings
                WHERE check_in_date <= %s
                  AND check_out_date > %s
                  AND booking_status IN ('in_house','confirmed')
                GROUP BY property_code
            """
            cur.execute(bookings_on_books_sql, [business_date, business_date])
            bob_map: Dict[str, int] = {
                r["property_code"]: _safe_int(r["bookings_on_books"]) for r in cur.fetchall()
            }

            # ---- Revenue: use total_amount if present for in-house stays (simple, demo-safe)
            # NOTE: Real PMS revenue is night-based and split by day; this is a safe placeholder.
            revenue_sql = """
                SELECT
                    property_code,
                    COALESCE(SUM(COALESCE(total_amount, nightly_rate * COALESCE(nights, 0))), 0) AS room_revenue
                FROM bookings
                WHERE check_in_date <= %s
                  AND check_out_date > %s
                  AND booking_status = 'in_house'
                GROUP BY property_code
            """
            cur.execute(revenue_sql, [business_date, business_date])
            rev_map: Dict[str, float] = {
                r["property_code"]: _safe_float(r["room_revenue"]) for r in cur.fetchall()
            }

            # ---- Prepare dynamic UPSERT into hotel_daily_kpi
            kpi_cols = _table_columns(cur, "hotel_daily_kpi")
            colset = set(kpi_cols)

            # base fields we want to write
            desired = [
                "property_code",
                "hotel_name",
                "business_date",
                "rooms_total",
                "rooms_sold",
                "rooms_available",
                "rooms_on_books",
                "bookings_on_books",
                "room_revenue",
                "adr",
                "revpar",
                "occupancy_pct",
                "fnb_revenue",
                "other_revenue",
                "total_revenue",
                "no_shows",
                "cancellations",
            ]
            write_cols = [c for c in desired if c in colset]

            if "property_code" not in colset or "business_date" not in colset:
                raise RuntimeError(
                    "hotel_daily_kpi must have at least (property_code, business_date)."
                )

            # conflict target (your table uses property_code + business_date)
            conflict_target = "(property_code, business_date)"

            def _compute_row(pcode: str, hname: str) -> Dict[str, object]:
                rooms_total = inv_map.get(pcode, 0)
                occupied = occ_map.get(pcode, 0)

                # Global PMS safety: never exceed inventory in KPI output
                rooms_sold = min(occupied, rooms_total) if rooms_total > 0 else occupied

                rooms_available = max(rooms_total - rooms_sold, 0)

                # new fields
                rooms_on_books = rob_map.get(pcode, 0)
                bookings_on_books = bob_map.get(pcode, 0)

                room_revenue = rev_map.get(pcode, 0.0)

                adr = (room_revenue / rooms_sold) if rooms_sold > 0 else 0.0
                revpar = (room_revenue / rooms_total) if rooms_total > 0 else 0.0
                occupancy_pct = (rooms_sold / rooms_total * 100.0) if rooms_total > 0 else 0.0

                fnb_revenue = 0.0
                other_revenue = 0.0
                total_revenue = room_revenue + fnb_revenue + other_revenue

                return {
                    "property_code": pcode,
                    "hotel_name": hname,
                    "business_date": business_date,
                    "rooms_total": rooms_total,
                    "rooms_sold": rooms_sold,
                    "rooms_available": rooms_available,
                    "rooms_on_books": rooms_on_books,
                    "bookings_on_books": bookings_on_books,
                    "room_revenue": room_revenue,
                    "adr": adr,
                    "revpar": revpar,
                    "occupancy_pct": occupancy_pct,
                    "fnb_revenue": fnb_revenue,
                    "other_revenue": other_revenue,
                    "total_revenue": total_revenue,
                    "no_shows": 0,
                    "cancellations": 0,
                }

            upserted = 0
            for h in hotels:
                pcode = h["property_code"]
                hname = h["hotel_name"]
                row = _compute_row(pcode, hname)

                cols_sql = ", ".join(write_cols)
                vals_sql = ", ".join(["%s"] * len(write_cols))
                updates_sql = ", ".join(
                    [
                        f"{c}=EXCLUDED.{c}"
                        for c in write_cols
                        if c not in ("property_code", "business_date")
                    ]
                )

                sql = f"""
                    INSERT INTO hotel_daily_kpi ({cols_sql})
                    VALUES ({vals_sql})
                    ON CONFLICT {conflict_target}
                    DO UPDATE SET {updates_sql}
                """

                cur.execute(sql, [row[c] for c in write_cols])
                upserted += 1

        conn.commit()
        return upserted
    finally:
        conn.close()


# -----------------------------
# CLI
# -----------------------------
def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate daily KPIs into hotel_daily_kpi")
    p.add_argument("--business-date", required=True, help="YYYY-MM-DD")
    p.add_argument(
        "--property-code", default="all", help="Property code like DRE001 or 'all'"
    )
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    biz = date.fromisoformat(args.business_date)
    rows = aggregate_day(biz, property_code=args.property_code)
    print(
        f"[AGG] hotel_daily_kpi upserted rows={rows} for business_date={biz} property={args.property_code}"
    )


if __name__ == "__main__":
    main()
