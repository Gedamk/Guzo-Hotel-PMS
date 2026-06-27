# -*- coding: utf-8 -*-
"""
guzo_backend/reports/daily_manager_pdf.py

Daily Manager Report (PDF) — Guzo Guest Assist (Ethiopian hotel context)

Upgrades vs older version:
- Reads DB settings from POSTGRES_* (primary) and GUZO_DB_* (fallback)
- Safer connection errors with clear message if password missing
- Defaults host to 127.0.0.1 (avoids IPv6 ::1 auth surprises)
- Writes PDF into <project_root>/reports_out/ with audit-friendly naming:
    daily-manager_<PROPERTY>_<YYYY-MM-DD>.pdf
- Pulls operational metrics from bookings table
- Attempts to pull housekeeping metrics if housekeeping tables exist
- Revenue remains optional (auto-detect if a known finance table exists; otherwise 0.00)

This module is safe to call from:
- FastAPI: /reports/daily-manager.pdf
- CLI scripts / scheduled jobs
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import psycopg2
from psycopg2.extras import RealDictCursor

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../Guzo
REPORTS_OUT_DIR = PROJECT_ROOT / "reports_out"
REPORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGO_PATH = PROJECT_ROOT / "assets" / "guzo_logo.png"


# -------------------------------------------------------------------
# Static hotel metadata (safe fallback until hotels table is fully wired)
# -------------------------------------------------------------------
PROPERTY_INFO: Dict[str, Dict[str, object]] = {
    "DRE001": {
        "name": "Dream Big Hotel",
        "city": "Addis Ababa",
        "country": "Ethiopia",
        "total_rooms": 60,
    },
    "N&N002": {
        "name": "N&N Luxury Hotel",
        "city": "Addis Ababa",
        "country": "Ethiopia",
        "total_rooms": 45,
    },
}


def get_property_meta(property_code: str) -> Dict[str, object]:
    info = PROPERTY_INFO.get(property_code)
    if not info:
        return {
            "name": f"Property {property_code}",
            "city": "Unknown City",
            "country": "Unknown Country",
            "total_rooms": 0,
        }
    return info


# -------------------------------------------------------------------
# DB connection helper
# -------------------------------------------------------------------
def _env_any(*keys: str, default: Optional[str] = None) -> Optional[str]:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            return v
    return default


def get_connection():
    """
    Open a PostgreSQL connection.

    Priority (matches your backend):
      POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT

    Backward compatible fallback:
      GUZO_DB_NAME, GUZO_DB_USER, GUZO_DB_PASSWORD, GUZO_DB_HOST, GUZO_DB_PORT
    """
    dbname = _env_any("POSTGRES_DB", "GUZO_DB_NAME", default="guzo_db")
    user = _env_any("POSTGRES_USER", "GUZO_DB_USER", default="guzo_user")
    password = _env_any("POSTGRES_PASSWORD", "GUZO_DB_PASSWORD", default=None)
    host = _env_any("POSTGRES_HOST", "GUZO_DB_HOST", default="127.0.0.1")
    port = _env_any("POSTGRES_PORT", "GUZO_DB_PORT", default="5432")

    # Normalize host: avoid ::1 surprises if user typed localhost
    if host.strip().lower() == "localhost":
        host = "127.0.0.1"

    if not password:
        raise RuntimeError(
            "No DB password supplied for Daily Manager PDF.\n"
            "Set environment variable POSTGRES_PASSWORD (recommended)\n"
            "or GUZO_DB_PASSWORD (fallback)."
        )

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        cursor_factory=RealDictCursor,
    )


# -------------------------------------------------------------------
# Helpers: detect tables/columns safely
# -------------------------------------------------------------------
def _table_exists(cur, table_name: str, schema: str = "public") -> bool:
    cur.execute(
        """
        SELECT EXISTS(
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = %s AND table_name = %s
        ) AS ok
        """,
        (schema, table_name),
    )
    row = cur.fetchone()
    return bool(row and row.get("ok"))


def _column_exists(cur, table_name: str, column_name: str, schema: str = "public") -> bool:
    cur.execute(
        """
        SELECT EXISTS(
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema = %s AND table_name = %s AND column_name = %s
        ) AS ok
        """,
        (schema, table_name, column_name),
    )
    row = cur.fetchone()
    return bool(row and row.get("ok"))


# -------------------------------------------------------------------
# Core metrics
# -------------------------------------------------------------------
@dataclass
class DailyMetrics:
    arrivals: int
    departures: int
    in_house: int
    rooms_in_house: int
    occupied_rooms: int
    available_rooms: int
    occupancy_pct: float

    hk_vacant_clean: int
    hk_vacant_dirty: int
    hk_occupied_dirty: int
    hk_vacant_inspected: int

    total_revenue_etb: float
    adr_etb: float
    revpar_etb: float

    alerts: List[str]


def fetch_daily_metrics(business_date: date, property_code: str) -> DailyMetrics:
    meta = get_property_meta(property_code)
    total_rooms = int(meta.get("total_rooms") or 0)

    alerts: List[str] = []

    conn = get_connection()
    try:
        cur = conn.cursor()

        # --- bookings metrics -------------------------------------------------
        # Arrivals: check_in_date = business_date
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM bookings
            WHERE property_code = %s
              AND check_in_date = %s
            """,
            (property_code, business_date),
        )
        arrivals = int(cur.fetchone().get("cnt") or 0)

        # Departures: check_out_date = business_date
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM bookings
            WHERE property_code = %s
              AND check_out_date = %s
            """,
            (property_code, business_date),
        )
        departures = int(cur.fetchone().get("cnt") or 0)

        # In-house: check_in_date < bd AND check_out_date > bd
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM bookings
            WHERE property_code = %s
              AND check_in_date < %s
              AND check_out_date > %s
            """,
            (property_code, business_date, business_date),
        )
        in_house = int(cur.fetchone().get("cnt") or 0)

        # Rooms checked in today (operational): arrivals count
        rooms_in_house = arrivals

        # Occupied rooms (simple operational): in_house + arrivals
        occupied_rooms = in_house + arrivals
        available_rooms = max(total_rooms - occupied_rooms, 0)
        occupancy_pct = (occupied_rooms / total_rooms * 100.0) if total_rooms > 0 else 0.0

        # --- housekeeping metrics (best-effort) ------------------------------
        hk_vacant_clean = hk_vacant_dirty = hk_occupied_dirty = hk_vacant_inspected = 0

        # Try housekeeping_status table first (used elsewhere in your project)
        # Expected columns (best guess):
        #   business_date, property_code, room_number, hk_status
        if _table_exists(cur, "housekeeping_status"):
            if _column_exists(cur, "housekeeping_status", "business_date") and _column_exists(cur, "housekeeping_status", "hk_status"):
                cur.execute(
                    """
                    SELECT hk_status, COUNT(*) AS cnt
                    FROM housekeeping_status
                    WHERE property_code = %s
                      AND business_date = %s
                    GROUP BY hk_status
                    """,
                    (property_code, business_date),
                )
                rows = cur.fetchall() or []
                for r in rows:
                    status = str(r.get("hk_status") or "").lower().strip()
                    cnt = int(r.get("cnt") or 0)

                    # Normalize common codes your UI uses:
                    # vacant_clean, vacant_dirty, occupied_dirty, vacant_inspected
                    if status in ("vacant_clean", "clean", "vc"):
                        hk_vacant_clean += cnt
                    elif status in ("vacant_dirty", "dirty", "vd"):
                        hk_vacant_dirty += cnt
                    elif status in ("occupied_dirty", "od"):
                        hk_occupied_dirty += cnt
                    elif status in ("vacant_inspected", "inspected", "vi"):
                        hk_vacant_inspected += cnt
            else:
                alerts.append("housekeeping_status table exists but missing expected columns (business_date, hk_status).")
        else:
            alerts.append("housekeeping_status table not found (HK metrics = 0).")

        # --- revenue (best-effort) -------------------------------------------
        # Default placeholder:
        total_revenue_etb = 0.0

        # If you later create a table like public.finance_charges with amount/currency/category,
        # this will auto-pick it up.
        if _table_exists(cur, "finance_charges"):
            needed = all(
                _column_exists(cur, "finance_charges", c)
                for c in ("property_code", "business_date", "amount", "currency")
            )
            if needed:
                # Prefer "room" category if exists
                has_category = _column_exists(cur, "finance_charges", "category")
                if has_category:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(amount), 0) AS total
                        FROM finance_charges
                        WHERE property_code = %s
                          AND business_date = %s
                          AND currency = 'ETB'
                          AND category = 'room'
                        """,
                        (property_code, business_date),
                    )
                else:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(amount), 0) AS total
                        FROM finance_charges
                        WHERE property_code = %s
                          AND business_date = %s
                          AND currency = 'ETB'
                        """,
                        (property_code, business_date),
                    )
                total_revenue_etb = float(cur.fetchone().get("total") or 0.0)
            else:
                alerts.append("finance_charges exists but missing expected columns (property_code, business_date, amount, currency).")

        # ADR / RevPAR
        adr_etb = (total_revenue_etb / occupied_rooms) if occupied_rooms > 0 else 0.0
        revpar_etb = (total_revenue_etb / total_rooms) if total_rooms > 0 else 0.0

        # Basic operational alerts
        if total_rooms == 0:
            alerts.append("Total rooms not configured for this property (occupancy% may be 0).")

        # If housekeeping shows too many dirty rooms, raise it
        if hk_vacant_dirty + hk_occupied_dirty >= 10:
            alerts.append("High dirty room count — consider prioritizing HK dispatch.")

        cur.close()

        return DailyMetrics(
            arrivals=arrivals,
            departures=departures,
            in_house=in_house,
            rooms_in_house=rooms_in_house,
            occupied_rooms=occupied_rooms,
            available_rooms=available_rooms,
            occupancy_pct=float(occupancy_pct),

            hk_vacant_clean=hk_vacant_clean,
            hk_vacant_dirty=hk_vacant_dirty,
            hk_occupied_dirty=hk_occupied_dirty,
            hk_vacant_inspected=hk_vacant_inspected,

            total_revenue_etb=float(total_revenue_etb),
            adr_etb=float(adr_etb),
            revpar_etb=float(revpar_etb),

            alerts=alerts,
        )
    finally:
        conn.close()


# -------------------------------------------------------------------
# PDF generation
# -------------------------------------------------------------------
def _output_path(business_date: date, property_code: str, output_path: Optional[str] = None) -> str:
    if output_path:
        return output_path

    out_name = f"daily-manager_{property_code}_{business_date.isoformat()}.pdf"
    return str(REPORTS_OUT_DIR / out_name)


def _draw_kv(c: canvas.Canvas, x: float, y: float, k: str, v: str, k_w: float = 65 * mm):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, k)
    c.setFont("Helvetica", 10)
    c.drawString(x + k_w, y, v)


def _draw_round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, fill, stroke=None):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.roundRect(x, y, w, h, 4 * mm, fill=1, stroke=1)


def _draw_metric_card(c: canvas.Canvas, x: float, y: float, w: float, h: float, label: str, value: str, fill):
    _draw_round_rect(c, x, y, w, h, fill, colors.HexColor("#d8d0c3"))
    c.setFillColor(colors.HexColor("#68727d"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 5 * mm, y + h - 8 * mm, label.upper())
    c.setFillColor(colors.HexColor("#1f2933"))
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x + 5 * mm, y + 8 * mm, value)


def _draw_section_title(c: canvas.Canvas, x: float, y: float, title: str):
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    c.setStrokeColor(colors.HexColor("#b9975b"))
    c.setLineWidth(1.2)
    c.line(x, y - 2 * mm, x + 174 * mm, y - 2 * mm)


def _draw_progress(c: canvas.Canvas, x: float, y: float, label: str, value: float, max_value: float, color):
    pct = min(max(value / max_value, 0), 1) if max_value else 0
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y + 1 * mm, label)
    c.setFillColor(colors.HexColor("#ece4d8"))
    c.roundRect(x + 48 * mm, y, 92 * mm, 4 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(color)
    c.roundRect(x + 48 * mm, y, 92 * mm * pct, 4 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x + 160 * mm, y + 1 * mm, f"{value:.0f}")


def generate_daily_manager_pdf(
    business_date: date,
    property_code: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate the Daily Manager PDF and return the file path.
    """
    meta = get_property_meta(property_code)
    hotel_name = str(meta.get("name"))
    city = str(meta.get("city"))
    country = str(meta.get("country"))
    total_rooms = int(meta.get("total_rooms") or 0)

    m = fetch_daily_metrics(business_date, property_code)
    pdf_path = _output_path(business_date, property_code, output_path)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    mx = 18 * mm
    y = height - 18 * mm

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(mx, y, "Daily Manager Report")
    y -= 7 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(mx, y, f"{hotel_name}")
    y -= 5 * mm

    c.setFont("Helvetica", 10)
    c.drawString(mx, y, f"{city}, {country}  •  Property: {property_code}")
    y -= 5 * mm
    c.drawString(mx, y, f"Business Date: {business_date.isoformat()}  •  Currency: ETB")
    y -= 10 * mm

    # Section 1: Rooms Summary
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "1) Rooms Summary")
    y -= 6 * mm

    _draw_kv(c, mx, y, "Total Rooms:", str(total_rooms)); y -= 5 * mm
    _draw_kv(c, mx, y, "Occupied Rooms:", str(m.occupied_rooms)); y -= 5 * mm
    _draw_kv(c, mx, y, "Available Rooms:", str(m.available_rooms)); y -= 5 * mm
    _draw_kv(c, mx, y, "Occupancy %:", f"{m.occupancy_pct:.1f}%"); y -= 8 * mm

    # Section 2: Movement Summary
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "2) Movement Summary")
    y -= 6 * mm

    _draw_kv(c, mx, y, "Arrivals:", str(m.arrivals)); y -= 5 * mm
    _draw_kv(c, mx, y, "Departures:", str(m.departures)); y -= 5 * mm
    _draw_kv(c, mx, y, "In-House:", str(m.in_house)); y -= 5 * mm
    _draw_kv(c, mx, y, "Rooms Checked-In:", str(m.rooms_in_house)); y -= 8 * mm

    # Section 3: Housekeeping Snapshot
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "3) Housekeeping Snapshot")
    y -= 6 * mm

    _draw_kv(c, mx, y, "Vacant Clean:", str(m.hk_vacant_clean)); y -= 5 * mm
    _draw_kv(c, mx, y, "Vacant Dirty:", str(m.hk_vacant_dirty)); y -= 5 * mm
    _draw_kv(c, mx, y, "Occupied Dirty:", str(m.hk_occupied_dirty)); y -= 5 * mm
    _draw_kv(c, mx, y, "Vacant Inspected:", str(m.hk_vacant_inspected)); y -= 8 * mm

    # Section 4: Rooms Revenue (best-effort)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "4) Rooms Revenue (Best-Effort)")
    y -= 6 * mm

    _draw_kv(c, mx, y, "Room Revenue:", f"{m.total_revenue_etb:,.2f}"); y -= 5 * mm
    _draw_kv(c, mx, y, "ADR:", f"{m.adr_etb:,.2f}"); y -= 5 * mm
    _draw_kv(c, mx, y, "RevPAR:", f"{m.revpar_etb:,.2f}"); y -= 8 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(mx, y, "Note: Revenue is 0.00 unless finance_charges is present and populated."); y -= 8 * mm

    # Alerts
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "5) Alerts / Notes")
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    if m.alerts:
        for a in m.alerts[:8]:
            c.drawString(mx, y, f"- {a}")
            y -= 5 * mm
            if y < 25 * mm:
                c.showPage()
                y = height - 18 * mm
                c.setFont("Helvetica", 10)
    else:
        c.drawString(mx, y, "- None")
        y -= 8 * mm

    # Sign-off
    if y < 55 * mm:
        c.showPage()
        y = height - 18 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx, y, "6) Sign-Off")
    y -= 9 * mm

    c.setFont("Helvetica", 10)
    c.drawString(mx, y, "Front Office Manager: ________________________________")
    y -= 9 * mm
    c.drawString(mx, y, "General Manager:      ________________________________")
    y -= 12 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(mx, 12 * mm, "Generated by Guzo Guest Assist • Daily Manager Report")

    c.showPage()
    c.save()
    return pdf_path
