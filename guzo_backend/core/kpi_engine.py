# guzo_backend/core/kpi_engine.py
#
# Central place to calculate daily ADR / RevPAR for a single property.

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TypedDict

import logging

from guzo_backend.db.postgres_bookings import get_connection
from guzo_backend.core.availability_engine import _fetch_rooms_total

logger = logging.getLogger(__name__)


class DailyKpi(TypedDict):
    property_code: str
    date: date
    rooms_sold: int
    revenue_total: float
    adr: float
    revpar: float


def _fetch_rooms_sold_and_revenue(property_code: str, target: date) -> tuple[int, float]:
    """
    Count how many room-nights are sold on a given date + total room revenue (ETB)
    for that date.

    - We assume 1 room per booking row.
    - We treat rate_per_night_etb as the revenue for that date.
    - We ignore bookings that are clearly cancelled / no-show.
    """
    sql = """
        SELECT
            COUNT(*) AS rooms_sold,
            COALESCE(SUM(rate_per_night_etb), 0) AS revenue_etb
        FROM bookings
        WHERE property_code = %s
          AND %s >= check_in_date
          AND %s < check_out_date
          AND (booking_status IS NULL OR booking_status NOT IN ('cancelled', 'no_show'))
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (property_code, target, target))
                row = cur.fetchone()
                if not row:
                    return 0, 0.0

                rooms_sold = int(row[0] or 0)
                revenue_etb_raw = row[1] or 0
                # row[1] will be Decimal from PostgreSQL
                revenue_etb = float(revenue_etb_raw) if isinstance(revenue_etb_raw, Decimal) else float(revenue_etb_raw)
                return rooms_sold, revenue_etb
    except Exception as e:
        logger.error(
            "Error fetching rooms_sold/revenue for %s on %s: %s",
            property_code,
            target,
            e,
        )
        return 0, 0.0


def compute_daily_kpi(property_code: str, target: date) -> DailyKpi:
    """
    Compute ADR / RevPAR for one property on one date.

    Definitions (room-division standard):
      - rooms_sold      = number of occupied rooms that night
      - revenue_total   = total room revenue (ETB) for that night
      - ADR             = revenue_total / rooms_sold
      - RevPAR          = revenue_total / rooms_total
    """
    # 1) How many rooms does the hotel have?
    rooms_total = _fetch_rooms_total(property_code)

    # 2) How many were sold & how much revenue?
    rooms_sold, revenue_total = _fetch_rooms_sold_and_revenue(property_code, target)

    # 3) Calculate ADR & RevPAR safely
    adr = revenue_total / rooms_sold if rooms_sold > 0 else 0.0
    revpar = revenue_total / rooms_total if rooms_total > 0 else 0.0

    return DailyKpi(
        property_code=property_code,
        date=target,
        rooms_sold=rooms_sold,
        revenue_total=round(revenue_total, 2),
        adr=round(adr, 2),
        revpar=round(revpar, 2),
    )
