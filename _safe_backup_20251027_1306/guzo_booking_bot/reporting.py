# -*- coding: utf-8 -*-
"""
Reporting utilities for Guzo Booking System:
- Generate branded PDF reports (with logo, tables, charts, trend arrows, recommendations, risk indicators)
- Export KPI history to CSV
- AI-driven insights (GPT if available, fallback heuristics)
"""

import os
import csv
from datetime import date
from typing import Dict, List

# Matplotlib (charts)
import matplotlib
matplotlib.use("Agg")  # headless mode
import matplotlib.pyplot as plt

# ReportLab (PDF generation)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Optional: GPT-powered insights
try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    AI_ENABLED = bool(openai.api_key)
except Exception:
    AI_ENABLED = False


# =========================
# Helpers
# =========================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _save_bar(labels, values, title, xlab, ylab, out_path, rotate_xticks=False):
    """Helper to save bar charts."""
    plt.figure()
    plt.bar(labels, values, color="#0E4D92")
    plt.title(title)
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    if rotate_xticks:
        plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _trend_arrow(current: float, last_week: float) -> str:
    """Return arrow indicator based on trend."""
    if last_week is None:
        return "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ"  # no comparison
    if current > last_week:
        return "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¬ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ"
    elif current < last_week:
        return "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ¬ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ"
    return "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ"


# =========================
# Charts
# =========================
def make_charts(data: Dict, out_dir: str) -> List[str]:
    """Generate charts and return their file paths."""
    ensure_dir(out_dir)
    out = []

    occ = data.get("occupancy_series", [])
    if occ:
        labels = [d[0] for d in occ]
        vals = [d[1] for d in occ]
        p = os.path.join(out_dir, "occupancy.png")
        _save_bar(labels, vals, "Occupancy by Day (%)", "Day", "Occupancy %", p)
        out.append(p)

    rev = data.get("revenue_by_channel", {})
    if rev:
        labels = list(rev.keys())
        vals = list(rev.values())
        p = os.path.join(out_dir, "revenue_by_channel.png")
        _save_bar(labels, vals, "Revenue by Channel (ETB)", "Channel", "ETB", p, rotate_xticks=True)
        out.append(p)

    return out


# =========================
# AI Insights & Recommendations
# =========================
def heuristic_insights(data: Dict) -> List[str]:
    """Fallback insights if GPT not available."""
    insights = []
    occ = data.get("occupancy_rate", 0)
    yoy_rev = data.get("yoy_revenue_pct", 0)
    rev_channels = data.get("revenue_by_channel", {})
    repeats = data.get("repeat_guests", 0)

    if occ < 50:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Occupancy below 50%: consider discounts or local promotions.")
    elif occ > 75:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Occupancy above 75%: test raising weekend rates by 5ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ10%.")

    if yoy_rev > 10:
        insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Revenue up {yoy_rev}% YoY: highlight growth to investors.")
    elif yoy_rev < 0:
        insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Revenue down {abs(yoy_rev)}% YoY: review OTA dependency and guest mix.")

    if rev_channels:
        top_channel = max(rev_channels, key=rev_channels.get)
        if top_channel.lower() == "direct":
            insights.append("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ Direct bookings strong: invest in loyalty campaigns.")
        else:
            insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {top_channel} dominates: manage commission costs carefully.")

    if repeats >= 5:
        insights.append("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ High repeat volume: consider perks like free breakfast or late checkout.")

    if not insights:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Stable performance. Monitor next week for shifts.")

    return insights


def generate_ai_insights(data: Dict) -> str:
    """Generate AI-driven insights or fallback to heuristics."""
    if AI_ENABLED:
        try:
            kpi_summary = (
                f"Weekly KPIs:\n"
                f"- Total Bookings: {data.get('total_bookings', 0)}\n"
                f"- Occupancy: {data.get('occupancy_rate', 0)}%\n"
                f"- Revenue: {data.get('revenue_total', 0)} ETB\n"
                f"- Cancellations: {data.get('cancellations', 0)}\n"
                f"- Repeat Guests: {data.get('repeat_guests', 0)}\n"
                f"- Top Channel: {data.get('top_channel', '-')}\n"
            )
            prompt = (
                "You are an AI assistant for hotel revenue managers. "
                "Generate 3ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ5 actionable insights based on the KPIs below. "
                "Focus on pricing, marketing, and guest retention strategies.\n\n"
                + kpi_summary
            )
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a hotel business intelligence assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.6,
            )
            return resp.choices[0].message["content"].strip()
        except Exception as e:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ GPT insights failed: {e}")
            return "\n".join(heuristic_insights(data))
    else:
        return "\n".join(heuristic_insights(data))


def generate_recommendations(data: Dict) -> str:
    """Suggest proactive actions for next week."""
    recs = []
    if data.get("occupancy_rate", 0) < 60:
        recs.append("Promote local packages to boost occupancy.")
    if data.get("top_channel", "").lower() == "ota":
        recs.append("Encourage direct bookings with discount codes.")
    if data.get("repeat_guests", 0) < 3:
        recs.append("Launch a simple loyalty program for rebookings.")
    if not recs:
        recs.append("Maintain current strategy and monitor competitor pricing.")
    return "\n".join(recs)


# =========================
# PDF Report
# =========================
def build_pdf(data: Dict, chart_paths: List[str], out_path: str, title: str = "Weekly Guzo Booking Report"):
    """Build a branded PDF report with KPIs, insights, recommendations, and charts."""
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Heading1"], textColor=colors.HexColor("#0E4D92"))
    normal_style = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=10, leading=14)
    footer_style = ParagraphStyle("Footer", parent=normal_style, textColor=colors.grey, fontSize=8, alignment=1)

    doc = SimpleDocTemplate(out_path, pagesize=A4, title=title)
    story = []

    # Cover Page
    story.append(Paragraph(f"{title}", header_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Date: {date.today().isoformat()}", normal_style))
    if data.get("property_name"):
        story.append(Paragraph(f"Property: {data['property_name']}", normal_style))
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Confidential Management Report", normal_style))
    story.append(PageBreak())

    # Weekly KPIs (with trend arrows + risk colors)
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly KPIs", header_style))
    kpis = [
        ["Total Bookings", f"{data.get('total_bookings', 0)} {_trend_arrow(data.get('total_bookings', 0), data.get('total_bookings_last_week'))}"],
        ["Occupancy Rate", f"{data.get('occupancy_rate', 0)} % {_trend_arrow(data.get('occupancy_rate', 0), data.get('occupancy_rate_last_week'))}"],
        ["Revenue (ETB)", f"ETB {data.get('revenue_total', 0):,} {_trend_arrow(data.get('revenue_total', 0), data.get('revenue_total_last_week'))}"],
        ["Cancellations", f"{data.get('cancellations', 0)} {_trend_arrow(data.get('cancellations', 0), data.get('cancellations_last_week'))}"],
        ["Repeat Guests", f"{data.get('repeat_guests', 0)} {_trend_arrow(data.get('repeat_guests', 0), data.get('repeat_guests_last_week'))}"],
        ["Top Channel", data.get("top_channel", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")],
    ]
    table = Table(kpis, colWidths=[2.8*inch, 3.2*inch])

    # Apply risk highlighting
    style = TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.grey)])
    occ = data.get("occupancy_rate", 0)
    if occ < 50:
        style.add("BACKGROUND", (1,1), (1,1), colors.HexColor("#FF9999"))  # red
    elif occ > 75:
        style.add("BACKGROUND", (1,1), (1,1), colors.HexColor("#99FF99"))  # green
    else:
        style.add("BACKGROUND", (1,1), (1,1), colors.HexColor("#FFFF99"))  # yellow

    table.setStyle(style)
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    # AI Insights
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ AI-Powered Insights", header_style))
    ai_text = generate_ai_insights(data)
    story.append(Paragraph(ai_text.replace("\n", "<br/>"), normal_style))
    story.append(Spacer(1, 0.3 * inch))

    # Recommendations
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Next Week Recommendations", header_style))
    recs = generate_recommendations(data)
    story.append(Paragraph(recs.replace("\n", "<br/>"), normal_style))
    story.append(Spacer(1, 0.3 * inch))

    # Charts
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Performance Charts", header_style))
    for p in chart_paths:
        story.append(Image(p, width=6.5*inch, height=3.2*inch))
        story.append(Spacer(1, 0.25 * inch))

    # Footer
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Generated by Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Smart Hospitality Analytics", footer_style))

    doc.build(story)
    print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ PDF report generated at {out_path}")


# =========================
# CSV Export
# =========================
def export_csv(data: Dict, out_csv_path: str):
    """Append KPI data into a CSV file (with header if new)."""
    ensure_dir(os.path.dirname(out_csv_path) or ".")
    row = {
        "date": date.today().isoformat(),
        "property_name": data.get("property_name", ""),
        "total_bookings": data.get("total_bookings", 0),
        "occupancy_rate": data.get("occupancy_rate", 0),
        "revenue_total": data.get("revenue_total", 0),
        "cancellations": data.get("cancellations", 0),
        "repeat_guests": data.get("repeat_guests", 0),
        "top_channel": data.get("top_channel", ""),
    }
    write_header = not os.path.exists(out_csv_path)
    with open(out_csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ CSV row appended at {out_csv_path}")

