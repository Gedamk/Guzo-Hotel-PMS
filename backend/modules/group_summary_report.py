# -*- coding: utf-8 -*-
"""
group_summary_report.py – Generate Group Summary PDF
----------------------------------------------------
Creates an executive-level summary report for all hotels
with performance KPIs and charts (Revenue by Hotel, City).
"""

import os
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

def generate_group_summary_pdf(group_df, total_kpis, output_path="reports/group_summary.pdf"):
    os.makedirs("reports", exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    logo_path = "dashboard/public/guzo_logo.png"
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=60))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Guzo Guest Assist – Group Performance Summary</b>", styles["Title"]))

    elements.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles["Normal"]))
    elements.append(Spacer(1, 12))

    # KPIs section
    kpi_data = [
        ["Total Revenue (ETB)", f"{total_kpis['total_revenue']:,.0f}"],
        ["Average ADR", f"{total_kpis['avg_adr']:,.0f}"],
        ["Average Occupancy %", f"{total_kpis['avg_occ']:,.1f}"],
        ["Average RevPAR", f"{total_kpis['avg_revpar']:,.0f}"]
    ]
    kpi_table = Table(kpi_data, colWidths=[200, 200])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))

    # Group dataframe
    elements.append(Paragraph("<b>Hotel Performance Table</b>", styles["Heading2"]))
    data = [group_df.columns.tolist()] + group_df.values.tolist()
    table = Table(data, colWidths=[120, 100, 90, 60, 90, 80])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E90FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))

    # Charts
    plt.figure(figsize=(6, 3))
    group_df.plot(kind="bar", x="Hotel Name", y="Revenue (ETB)", legend=False, color="skyblue")
    plt.title("Revenue by Hotel")
    plt.tight_layout()
    plt.savefig("reports/revenue_by_hotel.png", dpi=150)
    plt.close()

    elements.append(Image("reports/revenue_by_hotel.png", width=400, height=200))
    elements.append(Spacer(1, 12))

    plt.figure(figsize=(5, 3))
    city_df = group_df.groupby("City")["Revenue (ETB)"].sum().reset_index()
    plt.bar(city_df["City"], city_df["Revenue (ETB)"], color="orange")
    plt.title("Revenue by City")
    plt.tight_layout()
    plt.savefig("reports/revenue_by_city.png", dpi=150)
    plt.close()

    elements.append(Image("reports/revenue_by_city.png", width=380, height=200))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Prepared automatically by Guzo Guest Assist System", styles["Normal"]))
    elements.append(Paragraph("© 2025 Guzo Hospitality Tech Solutions", styles["Italic"]))

    doc.build(elements)
    print(f"✅ PDF generated: {output_path}")
    return output_path
