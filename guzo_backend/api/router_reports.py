"""
router_reports.py – Reporting API for daily KPIs.
"""

from fastapi import APIRouter
from datetime import date
from typing import Optional
from psycopg2.extras import DictCursor

from guzo_backend.db import get_connection

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def get_daily_report(
    business_date: Optional[date] = None,
):
    """
    Daily portfolio + per-hotel KPI summary from hotel_daily_kpi.
    """
    if business_date is None:
        business_date = date.today()

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            sql = """
                SELECT
                    h.property_code,
                    h.name AS hotel_name,
                    k.business_date,
                    k.rooms_total,
                    k.rooms_sold,
                    k.rooms_available,
                    k.room_revenue,
                    k.adr,
                    k.revpar,
                    k.occupancy_pct
                FROM hotel_daily_kpi k
                JOIN hotels h ON h.id = k.hotel_id
                WHERE k.business_date = %s
                ORDER BY h.property_code
            """
            cur.execute(sql, [business_date])
            rows = cur.fetchall()

        if not rows:
            return {
                "business_date": str(business_date),
                "summary": {},
                "per_hotel": [],
                "message": "No KPI data found – run aggregation job first.",
            }

        per_hotel = []
        total_rooms_total = 0
        total_rooms_sold = 0
        total_room_revenue = 0.0

        for r in rows:
            per_hotel.append(
                {
                    "property_code": r["property_code"],
                    "hotel_name": r["hotel_name"],
                    "business_date": str(r["business_date"]),
                    "rooms_total": r["rooms_total"],
                    "rooms_sold": r["rooms_sold"],
                    "rooms_available": r["rooms_available"],
                    "room_revenue": float(r["room_revenue"]),
                    "adr": float(r["adr"]),
                    "revpar": float(r["revpar"]),
                    "occupancy_pct": float(r["occupancy_pct"]),
                }
            )
            total_rooms_total += r["rooms_total"]
            total_rooms_sold += r["rooms_sold"]
            total_room_revenue += float(r["room_revenue"])

        rooms_available = total_rooms_total

        summary = {
            "property_code": "PORTFOLIO",
            "hotel_name": "All Hotels",
            "business_date": str(business_date),
            "rooms_total": total_rooms_total,
            "rooms_sold": total_rooms_sold,
            "rooms_available": rooms_available,
            "room_revenue": total_room_revenue,
            "adr": total_room_revenue / total_rooms_sold if total_rooms_sold else 0,
            "revpar": total_room_revenue / rooms_available if rooms_available else 0,
            "occupancy_pct": (total_rooms_sold / rooms_available * 100)
            if rooms_available
            else 0,
        }

        return {
            "business_date": str(business_date),
            "summary": summary,
            "per_hotel": per_hotel,
        }

    finally:
        conn.close()
