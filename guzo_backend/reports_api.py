# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Reports API (v2.0, DB-backed)

Exposes:
- GET  /health
- GET  /reports/portfolio?year=YYYY&month=MM
- GET  /reports/hotel?property_code=CODE&year=YYYY&month=MM
- GET  /bookings        → used by React Front Desk + BookingTable
- PATCH /bookings/{id}/status → front desk check-in / check-out

Data source priority:
1) PostgreSQL `bookings` table (via GUZO_DB_* env vars)
2) If DB fails or table missing → safe in-memory dummy data

This follows global hotel / Airbnb KPIs:
- Occupancy %
- ADR (Average Daily Rate)
- RevPAR
- Status lifecycle: confirmed → in_house → checked_out / cancelled / no_show
"""

import os
from datetime import date
from typing import List, Optional, Dict, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import psycopg2
from psycopg2.extras import RealDictCursor

# ======================================================
# FASTAPI APP + CORS
# ======================================================

app = FastAPI(title="Guzo Guest Assist Reports API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:8502",
    "http://127.0.0.1:8502",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# SIMPLE TOKEN CHECK
# ======================================================

API_TOKEN = os.getenv("REPORTS_API_TOKEN", "<REDACTED_DEMO_BEARER_TOKEN>")


def verify_token(authorization: Optional[str] = Header(None)) -> None:
    """
    Very simple auth for internal dashboards:

    - If no Authorization header → allow (local dev)
    - If present → must be "Bearer <REPORTS_API_TOKEN>"
    """
    if authorization is None:
        return

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


# ======================================================
# DB CONNECTION HELPER
# ======================================================

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


# ======================================================
# MODELS
# ======================================================

class Period(BaseModel):
    start_date: date
    end_date: date


class PortfolioSummary(BaseModel):
    bookings_count: int
    room_nights_sold: float
    room_revenue_etb: float
    rooms_total: int
    rooms_available: int
    adr: float
    revpar: float
    occupancy_pct: float  # 0–1


class PerHotelRow(BaseModel):
    property_code: str
    hotel_name: str
    bookings_count: int
    room_nights_sold: float
    room_revenue_etb: float
    rooms_total: int
    rooms_available: int
    adr: float
    revpar: float
    occupancy_pct: float  # 0–1


class PortfolioReport(BaseModel):
    scope: str  # "portfolio"
    year: int
    month: int
    period: Period
    summary: PortfolioSummary
    per_hotel: List[PerHotelRow]


class PortfolioReportResponse(BaseModel):
    year: int
    month: int
    scope: str
    report: PortfolioReport


class HotelReportResponse(BaseModel):
    year: int
    month: int
    property_code: str
    hotel_name: str
    period: Period
    summary: PerHotelRow


class Booking(BaseModel):
    id: int
    guest_name: str
    property_code: str
    hotel_name: str
    check_in: date
    check_out: date
    status: str  # "confirmed", "in_house", "checked_out", "cancelled", "no_show"
    channel: str
    total_amount_etb: float
    room_number: Optional[str] = None
    guest_note: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    new_status: str  # expected: confirmed / in_house / checked_out / cancelled / no_show


# ======================================================
# DUMMY DATA (SAFE FALLBACK)
# ======================================================

DUMMY_HOTELS: Dict[str, str] = {
    "DRE001": "Dream Big Hotel",
    "N&N002": "N&N Luxury Hotel",
}

DUMMY_BOOKINGS: List[Booking] = [
    Booking(
        id=1,
        guest_name="Anna Smith",
        property_code="DRE001",
        hotel_name="Dream Big Hotel",
        check_in=date(2025, 11, 3),
        check_out=date(2025, 11, 5),
        status="checked_out",
        channel="telegram",
        total_amount_etb=15000.0,
        room_number="201",
        guest_note="Prefers high floor.",
    ),
    Booking(
        id=2,
        guest_name="John Doe",
        property_code="DRE001",
        hotel_name="Dream Big Hotel",
        check_in=date(2025, 11, 10),
        check_out=date(2025, 11, 12),
        status="in_house",
        channel="instagram",
        total_amount_etb=18000.0,
        room_number="305",
        guest_note="Late check-in at 22:00.",
    ),
    Booking(
        id=3,
        guest_name="Marta K",
        property_code="N&N002",
        hotel_name="N&N Luxury Hotel",
        check_in=date(2025, 11, 21),
        check_out=date(2025, 11, 23),
        status="confirmed",
        channel="whatsapp",
        total_amount_etb=22000.0,
        room_number=None,
        guest_note="Allergic to peanuts.",
    ),
    Booking(
        id=4,
        guest_name="Abebe T",
        property_code="N&N002",
        hotel_name="N&N Luxury Hotel",
        check_in=date(2025, 11, 21),
        check_out=date(2025, 11, 22),
        status="cancelled",
        channel="direct",
        total_amount_etb=0.0,
        room_number=None,
        guest_note="Cancelled by guest.",
    ),
]


# ======================================================
# HELPERS
# ======================================================

def _month_period(year: int, month: int) -> Period:
    """
    Simple 30-day month period for now.
    Later you can use calendar.monthrange for exact days.
    """
    start = date(year, month, 1)
    end = date(year, month, 30)
    return Period(start_date=start, end_date=end)


def _row_get(row: Dict[str, Any], *keys: str, default=None):
    """
    Try multiple possible column names in the row dict.
    First non-empty wins. Example:

    hotel_name = _row_get(row, "hotel_name", "hotel", default="")
    """
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def load_bookings_from_db(limit: int = 500) -> List[Booking]:
    """
    Try to load bookings from PostgreSQL `bookings` table.

    EXPECTED columns (adjust to your real schema if needed):

      id                SERIAL / INT
      guest_name        TEXT
      property_code     TEXT       (ex: 'DRE001')
      hotel_name        TEXT       (ex: 'Dream Big Hotel')
      check_in_date     DATE
      check_out_date    DATE
      status            TEXT       ('confirmed', 'in_house', ...)
      channel           TEXT       ('telegram', 'instagram', 'direct', ...)
      total_amount_etb  NUMERIC
      room_number       TEXT (nullable)
      guest_note        TEXT (nullable)

    If anything fails → return DUMMY_BOOKINGS.
    """
    try:
        conn = get_connection()
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    guest_name,
                    property_code,
                    hotel_name,
                    check_in_date,
                    check_out_date,
                    status,
                    channel,
                    total_amount_etb,
                    room_number,
                    guest_note
                FROM bookings
                ORDER BY check_in_date DESC, id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    except Exception as e:
        # Log to console and fallback
        print(f"[ReportsAPI] DB load failed, using DUMMY_BOOKINGS. Error: {e}")
        return DUMMY_BOOKINGS

    results: List[Booking] = []
    for r in rows:
        results.append(
            Booking(
                id=r["id"],
                guest_name=_row_get(r, "guest_name", default=""),
                property_code=_row_get(r, "property_code", "hotel_property_code", default=""),
                hotel_name=_row_get(r, "hotel_name", "hotel", default=""),
                check_in=_row_get(r, "check_in_date", "check_in", default=date.today()),
                check_out=_row_get(r, "check_out_date", "check_out", default=date.today()),
                status=_row_get(r, "status", default="confirmed"),
                channel=_row_get(r, "channel", default="direct"),
                total_amount_etb=float(_row_get(r, "total_amount_etb", default=0.0) or 0.0),
                room_number=_row_get(r, "room_number", default=None),
                guest_note=_row_get(r, "guest_note", default=None),
            )
        )

    # If table exists but empty → return [] (no bookings)
    return results if results else []


def get_all_bookings() -> List[Booking]:
    """
    Main source for all endpoints.
    """
    bookings = load_bookings_from_db()
    # If DB call returns [] because of empty table, we still use []
    # If DB failed completely, load_bookings_from_db() already returned DUMMY_BOOKINGS.
    return bookings if bookings else DUMMY_BOOKINGS


def get_hotels_from_bookings(bookings: List[Booking]) -> Dict[str, str]:
    """
    Build property_code → hotel_name map from bookings.
    If no bookings, fall back to DUMMY_HOTELS.
    """
    hotel_map: Dict[str, str] = {}
    for b in bookings:
        if b.property_code and b.hotel_name and b.property_code not in hotel_map:
            hotel_map[b.property_code] = b.hotel_name

    if not hotel_map:
        return DUMMY_HOTELS

    return hotel_map


# ======================================================
# ENDPOINTS
# ======================================================

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "guzo_reports_api",
    }


@app.get("/reports/portfolio", response_model=PortfolioReportResponse)
def get_portfolio_report(
    year: int,
    month: int,
    _: None = Depends(verify_token),
) -> PortfolioReportResponse:
    """
    Portfolio report = multi-hotel KPIs.
    Uses all bookings from DB (or dummy fallback).
    """
    period = _month_period(year, month)
    bookings = get_all_bookings()
    hotel_map = get_hotels_from_bookings(bookings)

    per_hotel: List[PerHotelRow] = []

    for code, name in hotel_map.items():
        hotel_bookings = [b for b in bookings if b.property_code == code]

        bookings_count = len(hotel_bookings)
        room_nights_sold = sum(
            (b.check_out - b.check_in).days
            for b in hotel_bookings
            if b.status in ("confirmed", "in_house", "checked_out")
        )
        room_revenue_etb = sum(
            b.total_amount_etb
            for b in hotel_bookings
            if b.status != "cancelled"
        )

        # For now assume 60 rooms per property, 30 days:
        rooms_total = 60
        days_in_month = 30
        rooms_available = rooms_total * days_in_month

        adr = (room_revenue_etb / room_nights_sold) if room_nights_sold > 0 else 0.0
        revpar = (room_revenue_etb / rooms_available) if rooms_available > 0 else 0.0
        occupancy_pct = (room_nights_sold / rooms_available) if rooms_available > 0 else 0.0

        per_hotel.append(
            PerHotelRow(
                property_code=code,
                hotel_name=name,
                bookings_count=bookings_count,
                room_nights_sold=room_nights_sold,
                room_revenue_etb=room_revenue_etb,
                rooms_total=rooms_total,
                rooms_available=rooms_available,
                adr=adr,
                revpar=revpar,
                occupancy_pct=occupancy_pct,
            )
        )

    total_bookings = sum(h.bookings_count for h in per_hotel)
    total_room_nights = sum(h.room_nights_sold for h in per_hotel)
    total_revenue = sum(h.room_revenue_etb for h in per_hotel)
    total_rooms = sum(h.rooms_total for h in per_hotel)
    total_available = sum(h.rooms_available for h in per_hotel)

    summary = PortfolioSummary(
        bookings_count=total_bookings,
        room_nights_sold=total_room_nights,
        room_revenue_etb=total_revenue,
        rooms_total=total_rooms,
        rooms_available=total_available,
        adr=(total_revenue / total_room_nights) if total_room_nights > 0 else 0.0,
        revpar=(total_revenue / total_available) if total_available > 0 else 0.0,
        occupancy_pct=(total_room_nights / total_available) if total_available > 0 else 0.0,
    )

    report = PortfolioReport(
        scope="portfolio",
        year=year,
        month=month,
        period=period,
        summary=summary,
        per_hotel=per_hotel,
    )

    return PortfolioReportResponse(
        year=year,
        month=month,
        scope="portfolio",
        report=report,
    )


@app.get("/reports/hotel", response_model=HotelReportResponse)
def get_hotel_report(
    property_code: str,
    year: int,
    month: int,
    _: None = Depends(verify_token),
) -> HotelReportResponse:
    """
    Single-hotel monthly report.
    """
    bookings = get_all_bookings()
    hotel_map = get_hotels_from_bookings(bookings)

    if property_code not in hotel_map:
        raise HTTPException(status_code=404, detail="Unknown property_code")

    period = _month_period(year, month)
    name = hotel_map[property_code]

    hotel_bookings = [b for b in bookings if b.property_code == property_code]

    bookings_count = len(hotel_bookings)
    room_nights_sold = sum(
        (b.check_out - b.check_in).days
        for b in hotel_bookings
        if b.status in ("confirmed", "in_house", "checked_out")
    )
    room_revenue_etb = sum(
        b.total_amount_etb
        for b in hotel_bookings
        if b.status != "cancelled"
    )

    rooms_total = 60
    rooms_available = rooms_total * 30

    adr = (room_revenue_etb / room_nights_sold) if room_nights_sold > 0 else 0.0
    revpar = (room_revenue_etb / rooms_available) if rooms_available > 0 else 0.0
    occupancy_pct = (room_nights_sold / rooms_available) if rooms_available > 0 else 0.0

    summary_row = PerHotelRow(
        property_code=property_code,
        hotel_name=name,
        bookings_count=bookings_count,
        room_nights_sold=room_nights_sold,
        room_revenue_etb=room_revenue_etb,
        rooms_total=rooms_total,
        rooms_available=rooms_available,
        adr=adr,
        revpar=revpar,
        occupancy_pct=occupancy_pct,
    )

    return HotelReportResponse(
        year=year,
        month=month,
        property_code=property_code,
        hotel_name=name,
        period=period,
        summary=summary_row,
    )


@app.get("/bookings", response_model=List[Booking])
def list_bookings(
    _: None = Depends(verify_token),
) -> List[Booking]:
    """
    Live / recent bookings endpoint for Front Desk & BookingTable.
    """
    return get_all_bookings()


@app.patch("/bookings/{booking_id}/status", response_model=Booking)
def update_booking_status(
    booking_id: int = Path(..., description="Booking ID"),
    payload: BookingStatusUpdate = None,
    _: None = Depends(verify_token),
) -> Booking:
    """
    Status update endpoint for front desk check-in/check-out.

    Tries to UPDATE PostgreSQL; if DB fails, falls back to in-memory dummy list.
    """
    if payload is None:
        raise HTTPException(status_code=400, detail="No payload provided")

    allowed_statuses = {
        "confirmed",
        "in_house",
        "checked_out",
        "cancelled",
        "no_show",
    }

    if payload.new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {sorted(allowed_statuses)}",
        )

    # --- Try DB first ---
    try:
        conn = get_connection()
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE bookings
                SET status = %s
                WHERE id = %s
                RETURNING
                    id,
                    guest_name,
                    property_code,
                    hotel_name,
                    check_in_date,
                    check_out_date,
                    status,
                    channel,
                    total_amount_etb,
                    room_number,
                    guest_note
                """,
                (payload.new_status, booking_id),
            )
            row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Booking not found")

        updated = Booking(
            id=row["id"],
            guest_name=_row_get(row, "guest_name", default=""),
            property_code=_row_get(row, "property_code", "hotel_property_code", default=""),
            hotel_name=_row_get(row, "hotel_name", "hotel", default=""),
            check_in=_row_get(row, "check_in_date", "check_in", default=date.today()),
            check_out=_row_get(row, "check_out_date", "check_out", default=date.today()),
            status=_row_get(row, "status", default="confirmed"),
            channel=_row_get(row, "channel", default="direct"),
            total_amount_etb=float(_row_get(row, "total_amount_etb", default=0.0) or 0.0),
            room_number=_row_get(row, "room_number", default=None),
            guest_note=_row_get(row, "guest_note", default=None),
        )
        return updated

    except Exception as e:
        print(f"[ReportsAPI] DB update failed, falling back to dummy list. Error: {e}")

    # --- Fallback: update dummy list in-memory ---
    for i, b in enumerate(DUMMY_BOOKINGS):
        if b.id == booking_id:
            updated = b.copy(update={"status": payload.new_status})
            DUMMY_BOOKINGS[i] = updated
            return updated

    raise HTTPException(status_code=404, detail="Booking not found (dummy)")
