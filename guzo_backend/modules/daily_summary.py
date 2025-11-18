# -*- coding: utf-8 -*-
"""
daily_summary.py – Guzo Guest Assist Daily Summary Automation (v3.2)
--------------------------------------------------------------------
Generates and sends daily performance summaries via Email & Telegram.
Integrates with upgraded modules:
env_loader, google_sheets, email_sender, telegram_notifier.
"""

import os
import sys
import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------------------------------------------------------------
# Import project modules safely
# ---------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from guzo_backend.modules.env_loader import init_env
from guzo_backend.modules.google_sheets import init_client
from guzo_backend.modules.email_sender import send_email
from guzo_backend.modules.telegram_notifier import send_telegram_message

# ---------------------------------------------------------------------
# Main Process
# ---------------------------------------------------------------------
def main():
    """Main routine for daily summary automation."""
    init_env()
    print("🚀 Starting Guzo Guest Assist Daily Summary (v3.2)...")

    # Initialize Google Sheets client
    client = init_client()
    print("[GuzoSheets] ✅ Google Sheets client initialized successfully.")

    # Prepare date
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")

    # -----------------------------------------------------------------
    # 1️⃣ Load Hotel_Contacts_Master
    # -----------------------------------------------------------------
    try:
        master = client.open("Hotel_Contacts_Master").sheet1
        hotels = master.get_all_records()
    except Exception as e:
        print(f"❌ Error loading Hotel_Contacts_Master: {e}")
        return

    if not hotels:
        print("⚠️ No hotel data found in Hotel_Contacts_Master.")
        return

    report_lines = [f"Guzo Guest Assist Daily Summary\nDate: {today_str}\n\n"]

    # -----------------------------------------------------------------
    # 2️⃣ Process Each Active Hotel
    # -----------------------------------------------------------------
    for hotel in hotels:
        status = str(hotel.get("Integration Status", "")).strip().lower()
        if status not in ["✅ active", "active"]:
            continue

        hotel_name = hotel.get("Hotel Name", "Unnamed Hotel")
        sheet_id = hotel.get("Sheet ID")
        chat_id = str(hotel.get("Telegram Chat ID", "")).strip()
        email = hotel.get("Main Contact Email", "manager@guzoassist.com")

        print(f"[PROCESSING] {hotel_name}...")

        try:
            ws = client.open_by_key(sheet_id).worksheet("Bookings_Log")
            data = ws.get_all_records()
            if not data:
                print(f"⚠️ No data found in Bookings_Log for {hotel_name}")
                continue

            df = pd.DataFrame(data)
            df["Check-In Date"] = pd.to_datetime(df["Check-In Date"], errors="coerce")
            df["Total Revenue (ETB)"] = pd.to_numeric(df["Total Revenue (ETB)"], errors="coerce")

            today_df = df[df["Check-In Date"].dt.date == today]

            # Compute KPIs
            total_bookings = len(today_df)
            total_revenue = today_df["Total Revenue (ETB)"].sum()
            cancelled = len(df[df["Booking Status"].str.lower() == "cancelled"])
            unpaid = len(df[df["Payment Status"].str.lower() == "pending"])
            top_room = (
                today_df["Room Type"].value_counts().idxmax()
                if "Room Type" in today_df.columns and not today_df["Room Type"].empty
                else "N/A"
            )

            # Telegram message per hotel
            message = f"""
📅 *Daily Summary – {hotel_name}*
🏨 Date: {today_str}

• Bookings Today: {total_bookings}
• Revenue: {total_revenue:,.0f} ETB
• Top Room: {top_room}
• Cancelled: {cancelled}
• Unpaid Bookings: {unpaid}

🤖 Powered by Guzo Guest Assist
            """

            if chat_id:
                send_telegram_message(message, chat_id)
                print(f"✅ Telegram sent to {hotel_name} ({chat_id})")

            # Append to overall report summary
            report_lines.append(f"🏨 {hotel_name}\n")
            report_lines.append(f" - Bookings: {total_bookings}\n")
            report_lines.append(f" - Revenue: {total_revenue:,.0f} ETB\n")
            report_lines.append(f" - Cancelled: {cancelled}\n")
            report_lines.append(f" - Unpaid: {unpaid}\n")
            report_lines.append(f" - Top Room: {top_room}\n\n")

        except Exception as e:
            print(f"❌ Error processing {hotel_name}: {e}")

    # -----------------------------------------------------------------
    # 3️⃣ Generate PDF Summary Report
    # -----------------------------------------------------------------
    report_path = f"guzo_backend/reports/Daily_Summary_{today_str}.pdf"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(report_path, pagesize=A4)
    story = [Paragraph("📋 Guzo Guest Assist – Daily Summary", styles["Title"]), Spacer(1, 12)]

    for line in report_lines:
        story.append(Paragraph(line.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 8))

    doc.build(story)
    print(f"📄 PDF report generated: {report_path}")

    # -----------------------------------------------------------------
    # 4️⃣ Send Central Email (Admin Report)
    # -----------------------------------------------------------------
    subject = f"📊 Daily Summary Report – {today_str}"
    body = f"""
    <h3>📋 Guzo Guest Assist – Daily Summary ({today_str})</h3>
    <p>The attached PDF contains today's performance summary across all hotels.</p>
    <p>Automatically generated by Guzo Guest Assist.</p>
    """

    admin_email = os.getenv("TO_EMAIL", "owner@guzoassist.com")
    try:
        send_email(to_email=admin_email, subject=subject, body=body, pdf_path=report_path)
        print(f"📧 Summary emailed to admin: {admin_email}")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

    # -----------------------------------------------------------------
    # 5️⃣ Send Telegram Confirmation to Admin
    # -----------------------------------------------------------------
    try:
        send_telegram_message(f"✅ Daily summary generated and emailed for {today_str}.")
    except Exception as e:
        print(f"⚠️ Telegram notification failed: {e}")

    print("✅ Daily Summary task completed successfully!")


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
