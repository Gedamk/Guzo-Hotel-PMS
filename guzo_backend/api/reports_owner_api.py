# guzo_backend/api/reports_owner_api.py
#
# Monthly owner summary: rooms available, rooms sold, revenue, ADR, OCC%, RevPAR.

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import require_global_admin

import os
import psycopg2


def get_connection():
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


router = APIRouter(prefix="/reports", tags=["reports-owner"])


class OwnerSummaryRow(BaseModel):
    property_code: str
    year: int
    month: int
    rooms_available: int
    rooms_sold: int
    room_revenue_etb: float
    adr: float
    occ_pct: float
    revpar: float


def get_db_conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/owner_summary", response_model=List[OwnerSummaryRow])
def owner_summary(
    year: int,
    month: int,
    conn=Depends(get_db_conn),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    import calendar

    require_global_admin(db, user_email=x_pms_user_email)

    days_in_month = calendar.monthrange(year, month)[1]

    cur = conn.cursor()
    cur.execute(
        """
        WITH stays AS (
          SELECT
            property_code,
            check_in,
            check_out,
            total_amount_etb
          FROM bookings
          WHERE EXTRACT(YEAR FROM check_in) = %s
            AND EXTRACT(MONTH FROM check_in) = %s
        )
        SELECT
          h.property_code,
          COUNT(s.check_in) AS rooms_sold,
          COALESCE(SUM(s.total_amount_etb), 0) AS room_revenue_etb,
          h.total_rooms
        FROM hotels h
        LEFT JOIN stays s
          ON s.property_code = h.property_code
        GROUP BY h.property_code, h.total_rooms
        """,
        (year, month),
    )
    rows = cur.fetchall()
    cur.close()

    result: List[OwnerSummaryRow] = []
    for property_code, rooms_sold, revenue, total_rooms in rows:
        rooms_sold = rooms_sold or 0
        revenue = float(revenue or 0.0)
        total_rooms = total_rooms or 0
        rooms_available = total_rooms * days_in_month

        adr = revenue / rooms_sold if rooms_sold > 0 else 0.0
        occ_pct = (
            rooms_sold / rooms_available * 100.0 if rooms_available > 0 else 0.0
        )
        revpar = revenue / rooms_available if rooms_available > 0 else 0.0

        result.append(
            OwnerSummaryRow(
                property_code=property_code,
                year=year,
                month=month,
                rooms_available=rooms_available,
                rooms_sold=rooms_sold,
                room_revenue_etb=round(revenue, 2),
                adr=round(adr, 2),
                occ_pct=round(occ_pct, 1),
                revpar=round(revpar, 2),
            )
        )

    return result
