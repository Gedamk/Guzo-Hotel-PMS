# guzo_backend/routers/frontdesk.py
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.postgres_db import get_db

router = APIRouter(prefix="/frontdesk", tags=["frontdesk"])


class FrontdeskBooking(BaseModel):
    id: int
    guest_name: str
    check_in_date: date
    check_out_date: date
    booking_status: str
    property_code: str


class FrontdeskActionRequest(BaseModel):
    booking_id: int


def _parse_business_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format, expected YYYY-MM-DD",
        )


@router.get("/bookings", response_model=List[FrontdeskBooking])
def get_frontdesk_bookings(
    date: str = Query(..., description="Business date in YYYY-MM-DD format"),
    scope: str = Query("today", pattern="^(today|touches)$"),
    property: Optional[str] = Query(
        "ALL",
        alias="property",
        description="Property code (e.g. DRE001, N&N002) or ALL for portfolio",
    ),
    db: Session = Depends(get_db),
):
    business_date = _parse_business_date(date)

    where_clauses = [
        "check_in_date <= :bd",
        "check_out_date >= :bd",
    ]
    params = {"bd": business_date}

    if property and property.upper() != "ALL":
        where_clauses.append("property_code = :pc")
        params["pc"] = property

    where_sql = " AND ".join(where_clauses)

    sql = text(
        f"""
        SELECT
            id,
            guest_name,
            check_in_date,
            check_out_date,
            booking_status,
            property_code
        FROM bookings
        WHERE {where_sql}
        ORDER BY check_in_date, guest_name
        """
    )

    rows = db.execute(sql, params).fetchall()
    return [dict(row._mapping) for row in rows]


@router.post("/check-in", response_model=FrontdeskBooking)
def check_in_booking(
    payload: FrontdeskActionRequest, db: Session = Depends(get_db)
):
    select_sql = text(
        """
        SELECT
            id,
            guest_name,
            check_in_date,
            check_out_date,
            booking_status,
            property_code
        FROM bookings
        WHERE id = :id
        """
    )
    row = db.execute(select_sql, {"id": payload.booking_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_sql = text(
        """
        UPDATE bookings
        SET booking_status = 'in_house'
        WHERE id = :id
        """
    )
    db.execute(update_sql, {"id": payload.booking_id})
    db.commit()

    row = db.execute(select_sql, {"id": payload.booking_id}).fetchone()
    return dict(row._mapping)


@router.post("/check-out", response_model=FrontdeskBooking)
def check_out_booking(
    payload: FrontdeskActionRequest, db: Session = Depends(get_db)
):
    select_sql = text(
        """
        SELECT
            id,
            guest_name,
            check_in_date,
            check_out_date,
            booking_status,
            property_code
        FROM bookings
        WHERE id = :id
        """
    )
    row = db.execute(select_sql, {"id": payload.booking_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_sql = text(
        """
        UPDATE bookings
        SET booking_status = 'checked_out'
        WHERE id = :id
        """
    )
    db.execute(update_sql, {"id": payload.booking_id})
    db.commit()

    row = db.execute(select_sql, {"id": payload.booking_id}).fetchone()
    return dict(row._mapping)
