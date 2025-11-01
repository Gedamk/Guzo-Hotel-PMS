# -*- coding: utf-8 -*-
"""
Reporting utilities for Guzo Booking System:
- Generate branded PDF reports (with logo, tables, insights, charts)
- Export KPI history to CSV
- AI-driven insights (GPT if available, fallback heuristics)
- Competitor Benchmarking (manual now, OTA/STR ready for future)
"""

import os
import csv
from datetime import date
from typing import Dict, List
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Ensure matplotlib works headless
import matplotlib
matplotlib.use("Agg")

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


# =========================
# Charts
# =========================
def make_charts(data: Dict, out_dir: str) -> List[str]:
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
# AI Insights
# =========================
def heuristic_insights(data: Dict) -> List[str]:
    """Fallback heuristic insights if GPT not available."""
    insights = []
    occ = data.get("occupancy_rate", 0)
    yoy_rev = data.get("yoy_revenue_pct", 0)
    rev_channels = data.get("revenue_by_channel", {})
    repeats = data.get("repeat_guests", 0)

    if occ < 50:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Occupancy <50%: push weekday discounts or local promotions.")
    elif occ > 75:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Occupancy >75%: test raising weekend rates +5ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ10%.")

    if yoy_rev > 10:
        insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Revenue up {yoy_rev}% YoY: highlight direct growth to investors.")
    elif yoy_rev < 0:
        insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Revenue down {abs(yoy_rev)}% YoY: review OTA dependency and guest mix.")

    if rev_channels:
        top_channel = max(rev_channels, key=rev_channels.get)
        if top_channel.lower() == "direct":
            insights.append("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ Direct leads: invest in loyalty campaigns and rebooking emails.")
        else:
            insights.append(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {top_channel} dominates: manage commission costs carefully.")

    if repeats >= 5:
        insights.append("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ High repeat volume: consider loyalty perks (free breakfast, late checkout).")

    if not insights:
        insights.append("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Stable performance. Monitor next week for shifts.")

    return insights


def generate_ai_insights(data: Dict) -> str:
    """Generate AI insights using GPT if enabled, fallback to heuristics."""
    if AI_ENABLED:
        try:
            kpi_summary = (
                f"Weekly KPIs:\n"
                f"- Total Bookings: {data.get('total_bookings', 0)}\n"
                f"- Occupancy: {data.get('occupancy_rate', 0)}%\n"
                f"- Revenue: {data.get('revenue_total', 0)} ETB\n"
                f"- Cancellations: {data.get('cancellations', 0)}\n"
                f"- Repeat Guests: {data.get('repeat_guests', 0)}\n"
                f"- Top Channel: {data.get('top_channel', 'ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ')}\n"
                f"MTD: Bookings {data.get('mtd_bookings', 0)}, Revenue {data.get('mtd_revenue', 0)} ETB, Occ {data.get('mtd_occupancy', 0)}%\n"
                f"YoY: Bookings {data.get('yoy_bookings_pct', 0)}%, Revenue {data.get('yoy_revenue_pct', 0)}%, Occ {data.get('yoy_occupancy_pct', 0)}%\n"
            )
            prompt = (
                "You are an AI assistant for hotel revenue managers. "
                "Generate 3ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ5 actionable insights based on the KPIs below. "
                "Focus on pricing, marketing, and guest retention strategies. "
                "Be concise but professional.\n\n" + kpi_summary
            )
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a hotel business intelligence assistant."},
                          {"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.6,
            )
            return resp.choices[0].message["content"].strip()
        except Exception as e:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ GPT insights failed: {e}")
            return "\n".join(heuristic_insights(data))
    else:
        return "\n".join(heuristic_insights(data))


# =========================
# Competitor Benchmarking
# =========================
def get_competitor_benchmark(data: Dict) -> List[List[str]]:
    """Return competitor benchmarking values (manual, OTA, STR-ready)."""
    mode = os.getenv("BENCHMARK_MODE", "manual")

    # Your hotelÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂs KPIs
    your_occ = f"{data.get('occupancy_rate', 0)} %"
    your_adr = f"ETB {data.get('adr', 3200):,}"
    your_revpar = f"ETB {data.get('revpar', 2176):,}"

    if mode == "manual":
        market_occ = f"{os.getenv('BENCHMARK_MARKET_OCCUPANCY', '65')} %"
        market_adr = f"ETB {os.getenv('BENCHMARK_MARKET_ADR', '3450')}"
        market_revpar = f"ETB {os.getenv('BENCHMARK_MARKET_REVPAR', '2242')}"
    elif mode == "ota":
        # TODO: Implement OTA scraping or API integration (Booking.com, Expedia, etc.)
        market_occ, market_adr, market_revpar = "N/A", "N/A", "N/A"
    elif mode == "str":
        # TODO: Integrate STR Benchmarking API
        market_occ, market_adr, market_revpar = "N/A", "N/A", "N/A"
    else:
        market_occ, market_adr, market_revpar = "N/A", "N/A", "N/A"

    return [
        ["Your Occupancy", your_occ],
        ["Market Avg. Occupancy", market_occ],
        ["Your ADR", your_adr],
        ["Market Avg. ADR", market_adr],
        ["Your RevPAR", your_revpar],
        ["Market Avg. RevPAR", market_revpar],
    ]


# =========================
# PDF Report
# =========================
def build_pdf(data: Dict, chart_paths: List[str], out_path: str, title: str = "Weekly Guzo Booking Report"):
    """Build a branded management PDF with AI insights + competitor benchmarking."""

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Heading1"], textColor=colors.HexColor("#0E4D92"))
    normal_style = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=10, leading=14)
    footer_style = ParagraphStyle("Footer", parent=normal_style, textColor=colors.grey, fontSize=8, alignment=1)

    doc = SimpleDocTemplate(out_path, pagesize=A4, title=title)
    story = []

    # Cover
    logo_path = os.path.join("guzo_backend", "assets", "logo.png")
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=3*inch, height=1*inch))
        story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ {title}", header_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Date: {date.today().isoformat()}", normal_style))
    if data.get("property_name"):
        story.append(Paragraph(f"Property: {data['property_name']}", normal_style))
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Confidential Management Report", normal_style))
    story.append(PageBreak())

    # Weekly KPIs
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly KPIs", header_style))
    kpis = [
        ["Total Bookings", data.get("total_bookings", 0)],
        ["Occupancy Rate", f"{data.get('occupancy_rate', 0)} %"],
        ["Revenue (ETB)", f"ETB {data.get('revenue_total', 0):,}"],
        ["Cancellations", data.get("cancellations", 0)],
        ["Repeat Guests", data.get("repeat_guests", 0)],
        ["Top Channel", data.get("top_channel", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")],
    ]
    story.append(Table(kpis, colWidths=[2.8*inch, 3.2*inch]))
    story.append(Spacer(1, 0.3 * inch))

    # MTD + YoY
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Month-to-Date & YoY Trends", header_style))
    trends = [
        ["MTD Bookings", data.get("mtd_bookings", 0)],
        ["MTD Revenue (ETB)", f"ETB {data.get('mtd_revenue', 0):,}"],
        ["MTD Occupancy", f"{data.get('mtd_occupancy', 0)} %"],
        ["YoY Bookings ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ", f"{data.get('yoy_bookings_pct', 0)} %"],
        ["YoY Revenue ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ", f"{data.get('yoy_revenue_pct', 0)} %"],
        ["YoY Occupancy ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ", f"{data.get('yoy_occupancy_pct', 0)} %"],
    ]
    story.append(Table(trends, colWidths=[2.8*inch, 3.2*inch]))
    story.append(Spacer(1, 0.3 * inch))

    # Competitor Benchmarking
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Competitor Benchmarking", header_style))
    bench = get_competitor_benchmark(data)
    story.append(Table(bench, colWidths=[2.8*inch, 3.2*inch]))
    story.append(Spacer(1, 0.3 * inch))

    # AI Insights
    story.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ AI-Powered Insights", header_style))
    ai_text = generate_ai_insights(data)
    story.append(Paragraph(ai_text.replace("\n", "<br/>"), normal_style))
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


# =========================
# CSV Export
# =========================
def export_csv(data: Dict, out_csv_path: str):
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
        "mtd_bookings": data.get("mtd_bookings", 0),
        "mtd_revenue": data.get("mtd_revenue", 0),
        "mtd_occupancy": data.get("mtd_occupancy", 0),
        "yoy_bookings_pct": data.get("yoy_bookings_pct", 0),
        "yoy_revenue_pct": data.get("yoy_revenue_pct", 0),
        "yoy_occupancy_pct": data.get("yoy_occupancy_pct", 0),
        "adr": data.get("adr", 0),
        "revpar": data.get("revpar", 0),
    }
    write_header = not os.path.exists(out_csv_path)
    with open(out_csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
