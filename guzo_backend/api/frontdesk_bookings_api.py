# guzo_backend/api/frontdesk_bookings_api.py

from datetime import date
from typing import List, Literal

import logging
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from guzo_backend.core.postgres_db import engine

logger = logging.getLogger("frontdesk")

router = APIRouter(prefix="/frontdesk", tags=["frontdesk"])

ScopeType = Literal["today", "future", "all"]


def _parse_business_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {raw}. Use YYYY-MM-DD.")


@router.get("/bookings")
def get_frontdesk_bookings(
    scope: ScopeType = Query("today", description="today | future | all"),
    date_str: str = Query(..., alias="date", description="Business date in YYYY-MM-DD"),
) -> List[dict]:
    """
    Front Desk – bookings that *touch* the given business date.

    For now:
      - We ignore `scope` logic (today/future/all) and just show all bookings
        where check_in_date <= business_date <= check_out_date.
      - We return a flat list of rows; the React UI will bucket them
        into Arrivals / In-House / Departures.

    Later we can refine scope/status logic (e.g., cancelled, no-show, etc.).
    """

    business_date = _parse_business_date(date_str)

    logger.info("[frontdesk] Loading bookings for business_date=%s scope=%s", business_date, scope)

    sql = """
        SELECT
            b.id,
            b.confirmation_id,
            b.guest_name,
            b.check_in_date,
            b.check_out_date,
            b.booking_status,
            b.property_code,
            NULL::text AS room_number
        FROM bookings b
        WHERE
            b.check_in_date <= :business_date
            AND b.check_out_date >= :business_date
        ORDER BY
            b.check_in_date,
            b.id
    """

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(sql),
                {"business_date": business_date},
            )
            rows = result.fetchall()
    except Exception:
        logger.exception("[frontdesk] Error querying bookings")
        raise HTTPException(status_code=500, detail="Error loading front-desk bookings")

    bookings: List[dict] = []
    for row in rows:
        m = row._mapping
        bookings.append(
            {
                "id": m["id"],
                "confirmation_id": m["confirmation_id"],
                "guest_name": m["guest_name"],
                "check_in_date": m["check_in_date"].isoformat() if m["check_in_date"] else None,
                "check_out_date": m["check_out_date"].isoformat() if m["check_out_date"] else None,
                "booking_status": m["booking_status"],
                "property_code": m["property_code"],
                "room_number": m["room_number"],  # placeholder
            }
        )

    logger.info("[frontdesk] Returning %d bookings for %s", len(bookings), business_date)
    return bookings
