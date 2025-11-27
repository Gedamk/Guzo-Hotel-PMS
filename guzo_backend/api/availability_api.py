# guzo_backend/api/availability_api.py
#
# Single-property daily availability / house count endpoint.
# Used by FrontDeskHouseCount.tsx on the React side.
#
# Now:
#   - total_rooms comes from rooms table
#   - out_of_order_rooms = rooms with status = 'ooo'
#   - occupied_rooms from bookings table (booking_status)

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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


router = APIRouter(prefix="/rooms", tags=["rooms-availability"])


class AvailabilitySummary(BaseModel):
    property_code: str
    date: str  # "YYYY-MM-DD"
    total_rooms: int
    occupied_rooms: int
    out_of_order_rooms: int
    available_rooms: int
    occupancy_pct: float


@router.get("/availability", response_model=AvailabilitySummary)
def get_availability(
    property_code: str = Query(..., description="Hotel property code, e.g. DRE001"),
    target_date: Optional[str] = Query(
        None, description="Business date in YYYY-MM-DD, defaults to today"
    ),
):
    """
    Return a simple house-count style summary for one property on one date.
    """

    # parse date
    if target_date is None:
        business_date = date.today()
    else:
        try:
            business_date = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target_date format")

    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        cur = conn.cursor()

        # --- total_rooms from rooms table ------------------------------------
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS total_rooms
                FROM rooms
                WHERE property_code = %s
                """,
                (property_code,),
            )
            row = cur.fetchone()
            total_rooms = row[0] or 0
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"SQL error in total_rooms query: {e}"
            )

        if total_rooms == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No rooms defined for property_code={property_code}",
            )

        # --- out_of_order_rooms (OOO) ----------------------------------------
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS ooo_rooms
                FROM rooms
                WHERE property_code = %s
                  AND status = 'ooo'
                """,
                (property_code,),
            )
            row = cur.fetchone()
            out_of_order_rooms = row[0] or 0
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"SQL error in ooo_rooms query: {e}"
            )

        # --- occupied_rooms from bookings table ------------------------------
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS occupied_rooms
                FROM bookings b
                JOIN hotels h ON b.hotel_id = h.id
                WHERE h.property_code = %s
                  AND b.check_in_date <= %s
                  AND b.check_out_date > %s
                  AND b.booking_status IN ('in_house', 'checked_out', 'Confirmed', 'confirmed')
                """,
                (property_code, business_date, business_date),
            )
            row = cur.fetchone()
            occupied_rooms = row[0] or 0
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"SQL error in bookings query: {e}"
            )

        # --- final calculations ----------------------------------------------
        available_rooms = max(
            total_rooms - occupied_rooms - out_of_order_rooms, 0
        )
        occ_pct = (
            occupied_rooms / total_rooms * 100.0 if total_rooms > 0 else 0.0
        )

        cur.close()
    finally:
        conn.close()

    return AvailabilitySummary(
        property_code=property_code,
        date=business_date.isoformat(),
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        out_of_order_rooms=out_of_order_rooms,
        available_rooms=available_rooms,
        occupancy_pct=round(occ_pct, 1),
    )
