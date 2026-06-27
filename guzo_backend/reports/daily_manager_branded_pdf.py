# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from guzo_backend.reports.daily_manager_pdf import (
    PROJECT_ROOT,
    REPORTS_OUT_DIR,
    fetch_daily_metrics,
    get_property_meta,
)


def _output_path(business_date: date, property_code: str, output_path: Optional[str] = None) -> str:
    if output_path:
        return output_path
    return str(REPORTS_OUT_DIR / f"daily-manager_{property_code}_{business_date.isoformat()}.pdf")


def _metric_card(c: canvas.Canvas, x: float, y: float, w: float, h: float, label: str, value: str, fill):
    c.setFillColor(fill)
    c.setStrokeColor(colors.HexColor("#d8c38a"))
    c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#5b3b12"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 5 * mm, y + h - 8 * mm, label.upper())
    c.setFillColor(colors.HexColor("#1f2933"))
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x + 5 * mm, y + 8 * mm, value)


def _logo_placeholder(c: canvas.Canvas, x: float, y: float, w: float, h: float):
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#d8c38a"))
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=1)


def _purpose_band(c: canvas.Canvas, x: float, y: float, w: float, h: float, text: str):
    c.setFillColor(colors.HexColor("#fff8df"))
    c.setStrokeColor(colors.HexColor("#ead7a2"))
    c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#5b3b12"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 5 * mm, y + h - 6 * mm, "REPORT PURPOSE")
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica", 8.5)
    c.drawString(x + 5 * mm, y + 5 * mm, text[:132])


def _subheading(c: canvas.Canvas, x: float, y: float, title: str, note: str = ""):
    c.setFillColor(colors.HexColor("#5b3b12"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, title.upper())
    if note:
        c.setFillColor(colors.HexColor("#68727d"))
        c.setFont("Helvetica", 8)
        c.drawRightString(x + 174 * mm, y, note)


def _section(c: canvas.Canvas, x: float, y: float, title: str):
    c.setFillColor(colors.HexColor("#5b3b12"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    c.setStrokeColor(colors.HexColor("#d4af37"))
    c.setLineWidth(1.2)
    c.line(x, y - 2 * mm, x + 174 * mm, y - 2 * mm)


def _kv(c: canvas.Canvas, x: float, y: float, key: str, value: str, key_w: float = 65 * mm):
    c.setFillColor(colors.HexColor("#1f2933"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, key)
    c.setFont("Helvetica", 10)
    c.drawString(x + key_w, y, value)


def _progress(c: canvas.Canvas, x: float, y: float, label: str, value: float, max_value: float, color):
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


def _body_text(c: canvas.Canvas, x: float, y: float, text: str, max_width: int = 108, leading: float = 4.8 * mm) -> float:
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica", 9)
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > max_width:
            c.drawString(x, y, line)
            y -= leading
            line = word
        else:
            line = candidate
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def _audit_row(c: canvas.Canvas, x: float, y: float, label: str, status: str, note: str) -> float:
    c.setFillColor(colors.HexColor("#fff8df"))
    c.setStrokeColor(colors.HexColor("#ead7a2"))
    c.roundRect(x, y - 5 * mm, 174 * mm, 8 * mm, 2 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#5b3b12"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 4 * mm, y - 2 * mm, label)
    c.setFillColor(colors.HexColor("#27313b"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 58 * mm, y - 2 * mm, status)
    c.setFont("Helvetica", 8)
    c.drawString(x + 92 * mm, y - 2 * mm, note[:72])
    return y - 9 * mm


def _ensure_space(c: canvas.Canvas, y: float, height: float, minimum: float = 70 * mm) -> float:
    if y >= minimum:
        return y
    c.showPage()
    return height - 18 * mm


def generate_daily_manager_pdf(
    business_date: date,
    property_code: str,
    output_path: Optional[str] = None,
) -> str:
    meta = get_property_meta(property_code)
    hotel_name = str(meta.get("name"))
    city = str(meta.get("city"))
    country = str(meta.get("country"))
    total_rooms = int(meta.get("total_rooms") or 0)
    metrics = fetch_daily_metrics(business_date, property_code)
    pdf_path = _output_path(business_date, property_code, output_path)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    mx = 18 * mm
    y = height - 16 * mm

    c.setFillColor(colors.HexColor("#5b3b12"))
    c.rect(0, height - 43 * mm, width, 43 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#d4af37"))
    c.rect(0, height - 45 * mm, width, 2 * mm, fill=1, stroke=0)

    _logo_placeholder(c, mx, height - 35 * mm, 30 * mm, 22 * mm)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(mx + 36 * mm, y - 4 * mm, "Daily Manager Report")
    c.setFont("Helvetica", 10)
    c.drawString(mx + 36 * mm, y - 11 * mm, f"{hotel_name} | {city}, {country}")
    c.drawString(mx + 36 * mm, y - 17 * mm, f"Property: {property_code} | Business Date: {business_date.isoformat()} | Currency: ETB")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - mx, y - 8 * mm, "GUZO PMS")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - mx, y - 14 * mm, "Official PMS Daily Control Report")

    y = height - 66 * mm
    _purpose_band(
        c,
        mx,
        y,
        width - 2 * mx,
        16 * mm,
        "Prepared for General Manager review: operations, rooms, housekeeping, finance, exceptions, and Night Audit readiness.",
    )
    y -= 12 * mm

    _subheading(c, mx, y, "KPI Snapshot", "Live PMS metrics for the selected business date")
    y -= 27 * mm
    gap = 5 * mm
    card_w = (width - (2 * mx) - (3 * gap)) / 4
    card_h = 23 * mm
    _metric_card(c, mx, y, card_w, card_h, "Occupancy", f"{metrics.occupancy_pct:.1f}%", colors.HexColor("#fff8df"))
    _metric_card(c, mx + card_w + gap, y, card_w, card_h, "Arrivals", str(metrics.arrivals), colors.HexColor("#f7edcf"))
    _metric_card(c, mx + 2 * (card_w + gap), y, card_w, card_h, "Departures", str(metrics.departures), colors.HexColor("#fbf3df"))
    _metric_card(c, mx + 3 * (card_w + gap), y, card_w, card_h, "Revenue", f"{metrics.total_revenue_etb:,.0f}", colors.HexColor("#f4e2ac"))
    y -= 13 * mm

    _section(c, mx, y, "Executive Summary")
    y -= 8 * mm
    y = _body_text(
        c,
        mx,
        y,
        "This report summarizes the hotel business date from Guzo PMS. It supports the global hotel workflow of reviewing guest movement, room status, housekeeping readiness, revenue controls, alerts, and manager sign-off before Night Audit closes the date.",
    )
    y -= 3 * mm
    y = _audit_row(c, mx, y, "Front Desk", "Review", "Arrivals, departures, in-house guests, and no-shows.")
    y = _audit_row(c, mx, y, "Housekeeping", "Review", "Clean, dirty, occupied dirty, and inspected room status.")
    y = _audit_row(c, mx, y, "Finance", "Review", "Revenue, ADR, RevPAR, payments, and folio controls.")
    y -= 3 * mm

    y = _ensure_space(c, y, height, 80 * mm)
    _section(c, mx, y, "Rooms Summary")
    y -= 9 * mm
    _progress(c, mx, y, "Occupied", float(metrics.occupied_rooms), float(total_rooms or 1), colors.HexColor("#2f6b52")); y -= 8 * mm
    _progress(c, mx, y, "Available", float(metrics.available_rooms), float(total_rooms or 1), colors.HexColor("#0284c7")); y -= 8 * mm
    _kv(c, mx, y, "Total Rooms:", str(total_rooms)); y -= 6 * mm
    _kv(c, mx, y, "Occupancy %:", f"{metrics.occupancy_pct:.1f}%"); y -= 11 * mm

    y = _ensure_space(c, y, height, 75 * mm)
    _section(c, mx, y, "Guest Movement")
    y -= 9 * mm
    y = _body_text(
        c,
        mx,
        y,
        "Front Desk uses this section to verify the daily movement list before manager review and Night Audit. Arrivals, departures, and in-house counts should match the Front Desk module and reservation register.",
    )
    y -= 2 * mm
    _kv(c, mx, y, "Arrivals:", str(metrics.arrivals)); y -= 6 * mm
    _kv(c, mx, y, "Departures:", str(metrics.departures)); y -= 6 * mm
    _kv(c, mx, y, "In-House:", str(metrics.in_house)); y -= 6 * mm
    _kv(c, mx, y, "Rooms Checked-In:", str(metrics.rooms_in_house)); y -= 11 * mm

    y = _ensure_space(c, y, height, 75 * mm)
    _section(c, mx, y, "Housekeeping Snapshot")
    y -= 9 * mm
    y = _body_text(
        c,
        mx,
        y,
        "Housekeeping status supports room readiness and exception control. Occupied dirty or uninspected rooms should be reviewed as operational exceptions, not hidden from the daily report.",
    )
    y -= 2 * mm
    hk_w = (width - (2 * mx) - (3 * gap)) / 4
    hk_y = y - 18 * mm
    _metric_card(c, mx, hk_y, hk_w, 19 * mm, "Vacant Clean", str(metrics.hk_vacant_clean), colors.HexColor("#eef7f2"))
    _metric_card(c, mx + hk_w + gap, hk_y, hk_w, 19 * mm, "Vacant Dirty", str(metrics.hk_vacant_dirty), colors.HexColor("#fbf3df"))
    _metric_card(c, mx + 2 * (hk_w + gap), hk_y, hk_w, 19 * mm, "Occupied Dirty", str(metrics.hk_occupied_dirty), colors.HexColor("#fbefef"))
    _metric_card(c, mx + 3 * (hk_w + gap), hk_y, hk_w, 19 * mm, "Inspected", str(metrics.hk_vacant_inspected), colors.HexColor("#e0f2fe"))
    y -= 34 * mm

    y = _ensure_space(c, y, height, 75 * mm)
    _section(c, mx, y, "Rooms Revenue")
    y -= 9 * mm
    y = _body_text(
        c,
        mx,
        y,
        "Finance uses this section to confirm room revenue, ADR, and RevPAR for the business date. The values should reconcile with the Finance and Accounting Command Center before the day is locked.",
    )
    y -= 2 * mm
    _kv(c, mx, y, "Room Revenue:", f"{metrics.total_revenue_etb:,.2f}"); y -= 6 * mm
    _kv(c, mx, y, "ADR:", f"{metrics.adr_etb:,.2f}"); y -= 6 * mm
    _kv(c, mx, y, "RevPAR:", f"{metrics.revpar_etb:,.2f}"); y -= 11 * mm

    y = _ensure_space(c, y, height, 75 * mm)
    _section(c, mx, y, "Alerts and Notes")
    y -= 9 * mm
    y = _body_text(
        c,
        mx,
        y,
        "Alerts identify operational items requiring management attention. They should be reviewed together with Night Audit exceptions, pending guarantees, folio balances, and housekeeping readiness.",
    )
    y -= 2 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#1f2933"))
    if metrics.alerts:
        for alert in metrics.alerts[:6]:
            c.drawString(mx, y, f"- {alert}")
            y -= 5 * mm
    else:
        c.drawString(mx, y, "- None")
        y -= 6 * mm

    if y < 45 * mm:
        c.showPage()
        y = height - 18 * mm

    _section(c, mx, y, "Manager Sign-Off")
    y -= 11 * mm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#1f2933"))
    c.drawString(mx, y, "Prepared by Front Office Manager: ________________________________")
    y -= 9 * mm
    c.drawString(mx, y, "Reviewed by General Manager:      ________________________________")
    y -= 9 * mm
    c.drawString(mx, y, "Night Audit Review:              ________________________________")

    c.setFillColor(colors.HexColor("#68727d"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(mx, 12 * mm, "Generated by Guzo PMS | Daily Manager Report | Operations, Finance, Housekeeping, and Night Audit control")

    c.showPage()
    c.save()
    return pdf_path
