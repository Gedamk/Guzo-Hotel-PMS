# guzo_backend/api_frontdesk.py
from __future__ import annotations

import os
import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

import psycopg2
from psycopg2 import Error as PsycopgError

# Try to load .env so GUZO_DB_* and GUZO_ADMIN_TOKEN are available
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

# Resolve path to project root and .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if load_dotenv is not None:
    load_dotenv(ENV_PATH)


# ----------------------------------------
# DB connection helper
# ----------------------------------------


def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        raise RuntimeError("GUZO_DB_PASSWORD is not set in environment")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


# ----------------------------------------
# Auth helper (same token as dashboard)
# ----------------------------------------

ADMIN_TOKEN = os.getenv("GUZO_ADMIN_TOKEN", "<REDACTED_DEMO_BEARER_TOKEN>")


def verify_admin_token(authorization: str = Header(...)) -> None:
    """
    Very simple token check:
    Expects: Authorization: Bearer <token>
    """
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization[len(prefix):].strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )


# ----------------------------------------
# Pydantic models
# ----------------------------------------


class BookingOut(BaseModel):
    id: int
    booking_code: str
    guest_name: str
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    check_in: dt.date
    check_out: dt.date
    status: str
    channel: str
    total_amount_etb: float
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None
    notes: Optional[str] = None
    property_code: Optional[str] = None

    class Config:
        orm_mode = True  # pydantic v2 will just warn here


class BookingStatusUpdate(BaseModel):
    new_status: str


# ----------------------------------------
# Router
# ----------------------------------------

router = APIRouter()


# Small helper so we only write the SELECT → BookingOut mapping once
def _row_to_booking_out(row) -> BookingOut:
    (
        id_,
        booking_code_raw,
        guest_name,
        room_number,
        room_type,
        check_in,
        check_out,
        status_,
        channel,
        total_amount_etb,
        created_at,
        updated_at,
        notes,
        property_code,
    ) = row

    # If confirmation_id is NULL/empty, generate BK-{id}
    booking_code = (booking_code_raw or "").strip() or f"BK-{id_}"

    return BookingOut(
        id=id_,
        booking_code=booking_code,
        guest_name=guest_name,
        room_number=room_number or None,
        room_type=room_type or None,
        check_in=check_in,
        check_out=check_out,
        status=status_ or "",
        channel=channel or "",
        total_amount_etb=float(total_amount_etb or 0),
        created_at=created_at,
        updated_at=updated_at,
        notes=notes or None,
        property_code=property_code or None,
    )


# ----------------------------------------
# GET /frontdesk/bookings – snapshot for console
# ----------------------------------------


@router.get(
    "/bookings",  # API is mounted with prefix="/frontdesk" in main.py
    response_model=List[BookingOut],
    summary="Front desk bookings snapshot",
)
def frontdesk_bookings(scope: str = "today", _: None = Depends(verify_admin_token)):
    """
    Front desk console data source.

    scope:
      - today: all bookings that touch today (arrivals, in-house, departures)
      - inhouse: currently in-house (check_in_date <= today < check_out_date)
      - arrivals: check_in_date = today
      - departures: check_out_date = today
      - all: recent window (last 30 days + next 30 days)
    """
    scope = scope.lower().strip()
    if scope not in {"today", "inhouse", "arrivals", "departures", "all"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scope. Use: today, inhouse, arrivals, departures, all.",
        )

    today = dt.date.today()

    where_clauses: List[str] = []
    params: List[object] = []

    # Using real columns: check_in_date, check_out_date
    if scope == "today":
        # touches today
        where_clauses.append("b.check_in_date <= %s AND b.check_out_date >= %s")
        params.extend([today, today])
    elif scope == "inhouse":
        # currently staying tonight
        where_clauses.append("b.check_in_date <= %s AND b.check_out_date > %s")
        params.extend([today, today])
    elif scope == "arrivals":
        where_clauses.append("b.check_in_date = %s")
        params.append(today)
    elif scope == "departures":
        where_clauses.append("b.check_out_date = %s")
        params.append(today)
    elif scope == "all":
        start = today - dt.timedelta(days=30)
        end = today + dt.timedelta(days=30)
        where_clauses.append("b.check_in_date >= %s AND b.check_in_date <= %s")
        params.extend([start, end])

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Use real DB columns, with room_number as placeholder (no column in DB yet)
    sql = f"""
        SELECT
            b.id,
            b.confirmation_id AS booking_code_raw,
            b.guest_name,
            NULL::text AS room_number,                -- ✅ placeholder
            b.room_type,
            b.check_in_date AS check_in,
            b.check_out_date AS check_out,
            b.booking_status AS status,
            b.source AS channel,
            COALESCE(b.total_revenue_etb, 0) AS total_amount_etb,
            b.created_at,
            b.created_at AS updated_at,               -- no updated_at column yet
            NULL::text AS notes,
            b.property_code
        FROM bookings b
        {where_sql}
        ORDER BY b.check_in_date, b.guest_name;
    """

    try:
        rows: List[BookingOut] = []

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                result = cur.fetchall()
                for r in result:
                    rows.append(_row_to_booking_out(r))

        return rows

    except PsycopgError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e.pgerror or str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# ----------------------------------------
# PATCH /bookings/{id}/status – Check In / Check Out
# ----------------------------------------


@router.patch(
    "/bookings/{booking_id}/status",  # mounted under /frontdesk
    status_code=200,
    response_model=BookingOut,
    summary="Update booking status",
)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    _: None = Depends(verify_admin_token),
):
    """
    Update booking_status for a single booking.

    Typical transitions:
      - confirmed  → in_house     (Check In)
      - in_house   → checked_out  (Check Out)
      - confirmed  → cancelled
      - confirmed  → no_show
    """
    new_status = payload.new_status.strip().lower()

    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_status cannot be empty",
        )

    # Restrict allowed statuses (front desk friendly)
    allowed = {"confirmed", "in_house", "checked_out", "cancelled", "no_show"}
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(allowed))}",
        )

    update_sql = """
        UPDATE bookings
        SET booking_status = %s
        WHERE id = %s
        RETURNING
            id,
            confirmation_id AS booking_code_raw,
            guest_name,
            NULL::text AS room_number,
            room_type,
            check_in_date AS check_in,
            check_out_date AS check_out,
            booking_status AS status,
            source AS channel,
            COALESCE(total_revenue_etb, 0) AS total_amount_etb,
            created_at,
            created_at AS updated_at,
            NULL::text AS notes,
            property_code;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql, (new_status, booking_id))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Booking {booking_id} not found",
                    )

                conn.commit()
                return _row_to_booking_out(row)

    except PsycopgError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e.pgerror or str(e)}",
        )
    except HTTPException:
        # let 400/404 bubble up
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )
