# guzo_backend/routers/frontdesk.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_admin

from psycopg2.extras import RealDictCursor

from ..auth import get_current_admin  # your existing admin auth
from ..db.postgres_rooms import (
    assign_room_to_booking,
    apply_booking_status_transition,
    get_connection,
)

router = APIRouter(prefix="/frontdesk", tags=["frontdesk"])


# -------------------------------------------------------------------
# Pydantic models
# -------------------------------------------------------------------


class AssignRoomRequest(BaseModel):
    booking_id: int


class AssignRoomResponse(BaseModel):
    booking_id: int
    room_number: str


class BookingStatusUpdate(BaseModel):
    new_status: str


class FrontdeskBookingOut(BaseModel):
    """
    Shape matches what your React FrontDeskConsole expects as BackendBooking.
    """

    id: int
    booking_code: Optional[str]
    guest_name: str
    room_number: Optional[str]
    room_type: Optional[str]
    check_in: str          # "YYYY-MM-DD"
    check_out: str         # "YYYY-MM-DD"
    status: str
    channel: Optional[str]
    total_amount_etb: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    property_code: Optional[str] = None


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _fetch_frontdesk_booking_row(booking_id: int) -> dict:
    """
    Re-fetch a single booking row for front desk after a status change.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        b.id,
                        b.confirmation_id AS booking_code,
                        b.guest_name,
                        r.room_number,
                        b.room_type,
                        TO_CHAR(b.check_in_date, 'YYYY-MM-DD') AS check_in,
                        TO_CHAR(b.check_out_date, 'YYYY-MM-DD') AS check_out,
                        b.booking_status AS status,
                        b.source AS channel,
                        COALESCE(b.total_revenue_etb, 0) AS total_amount_etb,
                        TO_CHAR(b.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at,
                        TO_CHAR(b.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS updated_at,
                        NULL::text AS notes,
                        b.property_code
                    FROM bookings b
                    LEFT JOIN rooms r
                      ON r.booking_id = b.id
                    WHERE b.id = %s
                    """,
                    (booking_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Booking not found")
                return row
    finally:
        conn.close()


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@router.get("/bookings", response_model=List[FrontdeskBookingOut])
def list_frontdesk_bookings(
    scope: str = "today",
    user=Depends(get_current_admin),
):
    """
    Main endpoint used by FrontDeskConsole.tsx:
      GET /frontdesk/bookings?scope=today|inhouse|arrivals|departures|all

    'today' = any booking where today is between check_in and check_out
    'arrivals' = check_in is today
    'inhouse' = booking_status = 'in_house' and today between check_in & check_out
    'departures' = check_out is today
    'all' = +/- 30 days around today
    """

    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                conditions = []
                # You can adjust these rules to match your exact SOP later.
                if scope == "today":
                    conditions.append(
                        "b.check_in_date <= CURRENT_DATE AND b.check_out_date >= CURRENT_DATE"
                    )
                elif scope == "arrivals":
                    conditions.append("b.check_in_date = CURRENT_DATE")
                elif scope == "inhouse":
                    conditions.append(
                        "b.booking_status = 'in_house' "
                        "AND b.check_in_date <= CURRENT_DATE "
                        "AND b.check_out_date >= CURRENT_DATE"
                    )
                elif scope == "departures":
                    conditions.append(
                        "b.check_out_date = CURRENT_DATE "
                        "AND b.check_in_date <= CURRENT_DATE"
                    )
                elif scope == "all":
                    # +/- 30 days around today
                    conditions.append(
                        "b.check_in_date BETWEEN CURRENT_DATE - INTERVAL '30 days' "
                        "AND CURRENT_DATE + INTERVAL '30 days'"
                    )
                else:
                    # Fallback: behave like 'today'
                    conditions.append(
                        "b.check_in_date <= CURRENT_DATE AND b.check_out_date >= CURRENT_DATE"
                    )

                base_sql = """
                    SELECT
                        b.id,
                        b.confirmation_id AS booking_code,
                        b.guest_name,
                        r.room_number,
                        b.room_type,
                        TO_CHAR(b.check_in_date, 'YYYY-MM-DD') AS check_in,
                        TO_CHAR(b.check_out_date, 'YYYY-MM-DD') AS check_out,
                        b.booking_status AS status,
                        b.source AS channel,
                        COALESCE(b.total_revenue_etb, 0) AS total_amount_etb,
                        TO_CHAR(b.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at,
                        TO_CHAR(b.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS updated_at,
                        NULL::text AS notes,
                        b.property_code
                    FROM bookings b
                    LEFT JOIN rooms r
                      ON r.booking_id = b.id
                """

                if conditions:
                    base_sql += " WHERE " + " AND ".join(conditions)

                base_sql += " ORDER BY b.check_in_date, b.id"

                cur.execute(base_sql)
                rows = cur.fetchall() or []

                # FastAPI + Pydantic will coerce these dicts into FrontdeskBookingOut
                return rows

    finally:
        conn.close()


@router.post("/assign-room", response_model=AssignRoomResponse)
def assign_room_endpoint(
    payload: AssignRoomRequest,
    user=Depends(get_current_admin),
):
    """
    Assign a physical room to a booking.
    Frontend: 'Assign Room' button in FrontDeskConsole.
    """
    booking_id = payload.booking_id

    room_number = assign_room_to_booking(booking_id)

    if room_number is None:
        # No free room or booking not found
        raise HTTPException(
            status_code=400,
            detail="No available room for this booking or booking not found.",
        )

    return AssignRoomResponse(booking_id=booking_id, room_number=room_number)


@router.patch("/bookings/{booking_id}/status", response_model=FrontdeskBookingOut)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    user=Depends(get_current_admin),
):
    """
    Update booking_status (confirmed -> in_house -> checked_out, etc.)
    AND keep room.status in sync via apply_booking_status_transition.

    Called by:
      - 'Check In' button  (new_status = 'in_house')
      - 'Check Out' button (new_status = 'checked_out')
      - potentially 'cancelled', 'no_show', etc.
    """
    new_status = payload.new_status

    try:
        # 1) Apply lifecycle (updates bookings + rooms)
        apply_booking_status_transition(booking_id, new_status)
    except ValueError:
        raise HTTPException(status_code=404, detail="Booking not found")
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to apply status transition",
        )

    # 2) Re-fetch full row for frontend
    row = _fetch_frontdesk_booking_row(booking_id)
    return row
