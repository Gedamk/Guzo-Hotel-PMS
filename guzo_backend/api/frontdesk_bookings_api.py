# guzo_backend/api/frontdesk_bookings_api.py

from datetime import date
import re
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


def _booking_columns() -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'bookings'
    """
    with engine.begin() as conn:
        return {row[0] for row in conn.execute(text(sql)).fetchall()}


def _column_or_null(columns: set[str], column_name: str) -> str:
    if column_name in columns:
        return f"b.{column_name}"
    return "NULL::text"


def _amount_expression(columns: set[str]) -> str:
    available = [
        f"b.{column}"
        for column in ("total_amount", "total_amount_etb", "total_revenue_etb")
        if column in columns
    ]
    if not available:
        return "NULL::numeric"
    return f"COALESCE({', '.join(available)})"


def _numeric_column_or_null(columns: set[str], column_name: str) -> str:
    if column_name in columns:
        return f"b.{column_name}"
    return "NULL::numeric"


def _currency_from_notes(notes: str | None) -> str | None:
    match = re.search(r"Currency:\s*([A-Za-z]{3})", str(notes or ""), re.IGNORECASE)
    return match.group(1).upper() if match else None


@router.get("/bookings")
def get_frontdesk_bookings(
    scope: ScopeType = Query("today", description="today | future | all"),
    date_str: str = Query(..., alias="date", description="Business date in YYYY-MM-DD"),
    property_code: str | None = Query(None, description="Hotel property code, e.g. DRE001"),
    property_alias: str | None = Query(None, alias="property", description="Compatibility alias for property_code"),
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

    selected_property = (property_code or property_alias or "").strip().upper()
    logger.info(
        "[frontdesk] Loading bookings for business_date=%s scope=%s property=%s",
        business_date,
        scope,
        selected_property or "all",
    )
    columns = _booking_columns()
    property_filter = "AND b.property_code = :property_code" if selected_property else ""

    sql = f"""
        SELECT
            b.id,
            b.confirmation_id,
            b.guest_name,
            {_column_or_null(columns, "guest_email")} AS guest_email,
            b.check_in_date,
            b.check_out_date,
            b.booking_status,
            b.property_code,
            {_column_or_null(columns, "room_number")} AS room_number,
            COALESCE(
                {_column_or_null(columns, "source")},
                {_column_or_null(columns, "channel")}
            ) AS source,
            {_column_or_null(columns, "channel")} AS channel,
            {_column_or_null(columns, "room_type")} AS room_type,
            {_amount_expression(columns)} AS total_amount,
            {_numeric_column_or_null(columns, "rate_per_night_etb")} AS rate_per_night_etb,
            {_column_or_null(columns, "payment_method")} AS payment_method,
            {_column_or_null(columns, "payment_status")} AS payment_status,
            {_column_or_null(columns, "currency")} AS currency,
            {_column_or_null(columns, "notes")} AS notes
        FROM bookings b
        WHERE
            b.check_in_date <= :business_date
            AND b.check_out_date >= :business_date
            {property_filter}
        ORDER BY
            b.check_in_date,
            b.id
    """

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(sql),
                {"business_date": business_date, "property_code": selected_property},
            )
            rows = result.fetchall()
    except Exception:
        logger.exception("[frontdesk] Error querying bookings")
        raise HTTPException(status_code=500, detail="Error loading front-desk bookings")

    bookings: List[dict] = []
    for row in rows:
        m = row._mapping
        notes = m["notes"]
        stored_currency = str(m["currency"] or "").strip().upper()
        note_currency = _currency_from_notes(notes)
        effective_currency = note_currency or stored_currency or "ETB"
        bookings.append(
            {
                "id": m["id"],
                "confirmation_id": m["confirmation_id"],
                "guest_name": m["guest_name"],
                "guest_email": m["guest_email"],
                "check_in_date": m["check_in_date"].isoformat() if m["check_in_date"] else None,
                "check_out_date": m["check_out_date"].isoformat() if m["check_out_date"] else None,
                "booking_status": m["booking_status"],
                "property_code": m["property_code"],
                "room_number": m["room_number"],
                "source": m["source"],
                "channel": m["channel"],
                "room_type": m["room_type"],
                "total_amount": float(m["total_amount"]) if m["total_amount"] is not None else None,
                "rate_per_night_etb": float(m["rate_per_night_etb"]) if m["rate_per_night_etb"] is not None else None,
                "payment_method": m["payment_method"],
                "payment_status": m["payment_status"],
                "currency": effective_currency,
                "notes": notes,
            }
        )

    logger.info("[frontdesk] Returning %d bookings for %s", len(bookings), business_date)
    return bookings
