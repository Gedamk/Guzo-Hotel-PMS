# -*- coding: utf-8 -*-
"""
api_bookings.py – Booking management endpoints (status updates, etc.)
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import Error as PsycopgError

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


# -------------------------------------------------
# DB connection helper
# -------------------------------------------------
def get_connection():
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
      cursor_factory=RealDictCursor,
    )


# -------------------------------------------------
# Pydantic models
# -------------------------------------------------
class BookingStatusUpdate(BaseModel):
    new_status: str


router = APIRouter(
    prefix="/bookings",
    tags=["bookings"],
)

# Allowed states for front desk flow
ALLOWED_STATUSES = {
    "confirmed",
    "in_house",
    "checked_out",
    "cancelled",
    "no_show",
}


@router.patch("/{booking_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def update_booking_status(booking_id: int, payload: BookingStatusUpdate):
    """
    Update the status of a single booking.

    Uses the 'booking_status' column in the bookings table.
    Returns 204 No Content on success.
    """
    new_status = payload.new_status.strip().lower()

    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Must be one of: {sorted(ALLOWED_STATUSES)}",
        )

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bookings
                SET booking_status = %s
                WHERE id = %s
                """,
                (new_status, booking_id),
            )

            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Booking id {booking_id} not found",
                )

            conn.commit()

    except PsycopgError as e:  # type: ignore[name-defined]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while updating booking status: {e}",
        )
