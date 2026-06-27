# guzo_backend/api/debug_bookings_api.py

from typing import List

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.core.postgres_db import engine
from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import require_property_access

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/bookings_raw")
def bookings_raw(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
) -> List[dict]:
    """
    Return a raw dump of bookings (no filters).
    This is only for debugging to verify DB + engine + API wiring.
    """
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
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
        WHERE property_code = :property_code
        ORDER BY id
        LIMIT 50;
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql), {"property_code": property_code}).fetchall()

    return [dict(r._mapping) for r in rows]
