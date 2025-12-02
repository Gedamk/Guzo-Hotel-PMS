# guzo_backend/api/debug_bookings_api.py

from typing import List

from fastapi import APIRouter
from sqlalchemy import text

from guzo_backend.core.postgres_db import engine

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/bookings_raw")
def bookings_raw() -> List[dict]:
    """
    Return a raw dump of bookings (no filters).
    This is only for debugging to verify DB + engine + API wiring.
    """
    sql = """
        SELECT
            id,
            confirmation_id,
            guest_name,
            check_in_date,
            check_out_date,
            booking_status,
            property_code
        FROM bookings
        ORDER BY id
        LIMIT 50;
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql)).fetchall()

    return [dict(r._mapping) for r in rows]
