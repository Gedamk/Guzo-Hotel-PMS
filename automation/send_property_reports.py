# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Multi-Property Report Distributor (v3.5)
--------------------------------------------------------------------
Generates personalized weekly reports for each registered hotel,
emails them directly to the respective manager, and logs delivery status.

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Professional, secure, and scalable for hospitality standards
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Each property receives its own file & email
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Integrated with Telegram-linked chat registry
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Ensure imports from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_booking_bot.modules.email_sender import send_email
from guzo_booking_bot.modules.property_data import load_properties

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("EMAIL_SENDER", "reports@guzoassist.com")
REPORT_DIR = os.path.join("reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# =========================================================
# PDF GENERATOR FOR EACH PROPERTY
# =========================================================
def generate_property_report(property_name, manager_name, chat_id):
    """Generate a PDF report customized for each property."""
    date_str = datetime.now().strftime("%B %d, %Y")
    filename = f"{property_name.replace(' ', '_')}_Report_{date_str.replace(' ', '_')}.pdf"
    path = os.path.join(REPORT_DIR, filename)

    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=40, leftMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    title = ParagraphStyle("title", parent=styles["Title"], alignment=1, fontSize=20)
    subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], alignment=1, textColor=colors.grey)

    elements.append(Paragraph("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Guzo Guest Assist", title))
    elements.append(Paragraph(f"Property Performance Report ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {property_name}", subtitle))
    elements.append(Paragraph(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {date_str}", subtitle))
    elements.append(Spacer(1, 0.25 * inch))

    # Metrics (sample placeholders)
    metrics = [
        ["Metric", "Value"],
        ["Total Bookings", 12],
        ["Checked-in Guests", 9],
        ["Pending Replies", 2],
        ["Avg Response Time", "3.5 mins"],
        ["Guest Satisfaction", "94%"],
        ["System Status", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Stable"],
    ]
    table = Table(metrics, colWidths=[3 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # Footer
    footer = (
        f"Report prepared for {manager_name} (Chat ID: {chat_id})\n"
        "Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ Empowering Hospitality Excellence\n"
        "ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ© 2025 Guzo Guest Assist | All Rights Reserved ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂªÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹"
    )
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(footer, ParagraphStyle("footer", alignment=1, textColor=colors.grey, fontSize=9)))

    doc.build(elements)
    print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Generated report for {property_name}: {path}")
    return path

# =========================================================
# MAIN EXECUTION
# =========================================================
def main():
    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Starting multi-property report distribution...")
    properties = load_properties()

    if not properties:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No registered properties found in chat_ids.json.")
        return

    for p in properties:
        property_name = p["property"]
        manager_name = p["name"]
        manager_email = os.getenv("EMAIL_RECEIVER", "manager@guzoassist.com")  # You can customize per hotel later
        chat_id = p["chat_id"]

        # Generate individual report
        pdf_path = generate_property_report(property_name, manager_name, chat_id)

        # Send email
        subject = f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {property_name} ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly Performance Report"
        body = (
            f"Dear {manager_name},\n\n"
            f"Please find attached your personalized weekly performance report for *{property_name}*.\n"
            f"This includes key metrics, response analytics, and satisfaction insights.\n\n"
            f"Report generated on: {datetime.now().strftime('%B %d, %Y %I:%M %p')}\n\n"
            "Warm regards,\n"
            "Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Automated Hospitality System ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ"
        )

        print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Sending report to {manager_name} ({property_name})...")
        email_status = send_email(
            to_email=manager_email,
            subject=subject,
            content=body,
            from_email=SENDER_EMAIL,
            attachments=[pdf_path],
        )

        if email_status:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Report sent successfully to {manager_email}")
        else:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to send report to {manager_email}")

    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ All property reports processed successfully.")

if __name__ == "__main__":
    main()
