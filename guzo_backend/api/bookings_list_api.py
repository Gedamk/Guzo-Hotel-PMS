# guzo_backend/api/bookings_list_api.py
#
# Front desk bookings feed used by React FrontDeskBookings.tsx.
# Now includes assigned room_number from room_assignments table.

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from guzo_backend.core.postgres_bookings import get_connection

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-bookings"])


class FrontDeskBooking(BaseModel):
    id: int
    booking_code: Optional[str] = None
    guest_name: str
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    check_in: date
    check_out: date
    status: str
    channel: Optional[str] = None
    total_amount_etb: float
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
    property_code: str


@router.get("/bookings", response_model=List[FrontDeskBooking])
def list_frontdesk_bookings(
    scope: str = Query(
        "today",
        description="Currently only 'today' is supported; reserved for future scopes.",
    ),
    date_str: Optional[str] = Query(
        None, alias="date", description="Business date in YYYY-MM-DD"
    ),
):
    """
    Return bookings around the given business date, across all properties.

    We:
    - pull from PostgreSQL bookings table
    - join hotels to get property_code
    - LEFT JOIN room_assignments to get room_number (if assigned)
    """

    if scope != "today":
        raise HTTPException(status_code=400, detail="Only scope='today' is supported")

    # Parse date (default = today)
    if date_str:
        try:
            business_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        business_date = date.today()

    try:
        conn = get_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

    try:
        with conn.cursor() as cur:
            # Strategy:
            # - Include bookings that overlap the business date
            #   OR start within the next 7 days (future arrivals).
            # - Join hotels for property_code.
            # - LEFT JOIN room_assignments to include current room_number.
            cur.execute(
                """
                SELECT
                    b.id,
                    b.confirmation_id AS booking_code,
                    b.guest_name,
                    ra.room_number,
                    b.room_type,
                    b.check_in_date AS check_in,
                    b.check_out_date AS check_out,
                    COALESCE(b.booking_status, 'confirmed') AS status,
                    NULL::text AS channel,
                    COALESCE(b.total_revenue_etb, 0) AS total_amount_etb,
                    -- we don't yet store created_at/updated_at separately;
                    -- approximate with check_in/check_out so the API shape matches the UI.
                    b.check_in_date::timestamptz AS created_at,
                    b.check_out_date::timestamptz AS updated_at,
                    NULL::text AS notes,
                    h.property_code
                FROM bookings b
                JOIN hotels h
                    ON b.hotel_id = h.id
                LEFT JOIN room_assignments ra
                    ON ra.booking_id = b.id
                WHERE
                    (
                        -- stays overlapping the business date
                        b.check_in_date <= %(biz)s
                        AND b.check_out_date > %(biz)s
                    )
                    OR
                    (
                        -- near-future arrivals (within 7 days)
                        b.check_in_date > %(biz)s
                        AND b.check_in_date <= %(biz_plus_7)s
                    )
                ORDER BY
                    b.check_in_date,
                    b.id
                """,
                {
                    "biz": business_date,
                    "biz_plus_7": business_date.replace(day=business_date.day)  # just to satisfy mapping, we will override below
                },
            )

            # NOTE: Python's date.replace(day=...) used above is a bit silly; simpler is:
            # but since we can't import relativedelta here easily, we'll just recompute:
            # Re-run with a safer calculation:
        # Quick re-open cursor with corrected parameter usage
        conn.rollback()
        with conn.cursor() as cur:
            from datetime import timedelta

            biz = business_date
            biz_plus_7 = business_date + timedelta(days=7)

            cur.execute(
                """
                SELECT
                    b.id,
                    b.confirmation_id AS booking_code,
                    b.guest_name,
                    ra.room_number,
                    b.room_type,
                    b.check_in_date AS check_in,
                    b.check_out_date AS check_out,
                    COALESCE(b.booking_status, 'confirmed') AS status,
                    NULL::text AS channel,
                    COALESCE(b.total_revenue_etb, 0) AS total_amount_etb,
                    b.check_in_date::timestamptz AS created_at,
                    b.check_out_date::timestamptz AS updated_at,
                    NULL::text AS notes,
                    h.property_code
                FROM bookings b
                JOIN hotels h
                    ON b.hotel_id = h.id
                LEFT JOIN room_assignments ra
                    ON ra.booking_id = b.id
                WHERE
                    (
                        b.check_in_date <= %(biz)s
                        AND b.check_out_date > %(biz)s
                    )
                    OR
                    (
                        b.check_in_date > %(biz)s
                        AND b.check_in_date <= %(biz_plus_7)s
                    )
                ORDER BY
                    b.check_in_date,
                    b.id
                """,
                {
                    "biz": biz,
                    "biz_plus_7": biz_plus_7,
                },
            )

            rows = cur.fetchall()

        result: List[FrontDeskBooking] = []
        for row in rows:
            (
                booking_id,
                booking_code,
                guest_name,
                room_number,
                room_type,
                check_in,
                check_out,
                status,
                channel,
                total_amount_etb,
                created_at,
                updated_at,
                notes,
                property_code,
            ) = row

            result.append(
                FrontDeskBooking(
                    id=booking_id,
                    booking_code=booking_code,
                    guest_name=guest_name,
                    room_number=room_number,
                    room_type=room_type,
                    check_in=check_in,
                    check_out=check_out,
                    status=status,
                    channel=channel,
                    total_amount_etb=float(total_amount_etb or 0),
                    created_at=created_at,
                    updated_at=updated_at,
                    notes=notes,
                    property_code=property_code,
                )
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL error in frontdesk bookings: {e}")
    finally:
        conn.close()
