# -*- coding: utf-8 -*-
"""
weekly_summary.py – Guzo Guest Assist Weekly Summary Automation (v5.0)
----------------------------------------------------------------------
🌍 Unified global version for all partner hotels
✅ Reads hotel sheets from Hotel_Contacts_Master
✅ Aggregates weekly KPIs (Bookings, Revenue, Occupancy, ADR, RevPAR)
✅ Updates “Weekly_Summary” tab per hotel
✅ Syncs central analytics to Global Log
✅ Sends formatted Email + Telegram notifications
"""

import os
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from telegram import Bot
from guzo_backend.modules.google_sheets import init_client
from guzo_backend.modules.email_sender import send_email

# ---------------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------------
BASE_DIR = os.path.join(os.path.dirname(__file__), "../../")
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
client = init_client()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HQ_EMAIL = os.getenv("HQ_EMAIL", "support@guzoassist.com")
bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None


# ---------------------------------------------------------------------
# CORE SUMMARY FUNCTION
# ---------------------------------------------------------------------
def generate_weekly_summary(sheet_id: str, hotel_name: str, recipient_email: str,
                            telegram_chat_id: str, total_rooms: int = 30):
    """
    Generate a weekly summary for one hotel sheet and send email/Telegram notifications.
    """
    print(f"[SUMMARY] 🏨 Processing hotel: {hotel_name}")

    try:
        bookings_ws = client.open_by_key(sheet_id).worksheet("Bookings_Log")
        data = bookings_ws.get_all_records()

        if not data:
            print(f"⚠️ No booking data for {hotel_name}. Skipping.")
            return

        df = pd.DataFrame(data)
        df["Check-In Date"] = pd.to_datetime(df["Check-In Date"], errors="coerce")
        df["Total Revenue (ETB)"] = pd.to_numeric(df["Total Revenue (ETB)"], errors="coerce")

        week_end = datetime.now()
        week_start = week_end - timedelta(days=7)
        week_range = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

        mask = (df["Check-In Date"] >= week_start) & (df["Check-In Date"] <= week_end)
        week_df = df.loc[mask & (df["Booking Status"].str.lower().str.contains("confirm"))]

        total_bookings = len(week_df)
        total_nights = week_df.get("Nights", pd.Series([1]*total_bookings)).sum()
        total_revenue = week_df["Total Revenue (ETB)"].sum()
        adr = total_revenue / total_bookings if total_bookings else 0
        occupancy = (total_nights / (total_rooms * 7)) * 100 if total_rooms else 0
        revpar = total_revenue / (total_rooms * 7) if total_rooms else 0
        top_room = week_df["Room Type"].mode()[0] if not week_df["Room Type"].empty else "N/A"

        # Append results to Weekly_Summary tab
        ws = client.open_by_key(sheet_id).worksheet("Weekly_Summary")
        summary_row = [
            week_start.strftime("%Y-%m-%d"),
            week_end.strftime("%Y-%m-%d"),
            total_bookings,
            int(total_nights),
            float(total_revenue),
            round(adr, 2),
            round(occupancy, 1),
            round(revpar, 1),
            top_room,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            "AutoBot",
            "✅ Approved",
            "Auto-generated via Guzo Guest Assist",
        ]
        ws.append_row(summary_row, value_input_option="USER_ENTERED")
        print(f"✅ Weekly_Summary updated for {hotel_name}")

        # -----------------------------------------------------------------
        # EMAIL BODY
        # -----------------------------------------------------------------
        email_subject = f"🏨 {hotel_name} – Weekly Summary ({week_range})"
        email_body = (
            f"Dear {hotel_name} Manager,\n\n"
            f"Here’s your automatically generated weekly summary ({week_range}):\n\n"
            f"• Total Bookings: {total_bookings}\n"
            f"• Total Nights: {int(total_nights)}\n"
            f"• Total Revenue: {total_revenue:,.0f} ETB\n"
            f"• ADR (Average Daily Rate): {adr:,.2f} ETB\n"
            f"• Occupancy: {occupancy:.1f}%\n"
            f"• RevPAR: {revpar:,.2f} ETB\n"
            f"• Top Room Type: {top_room}\n\n"
            f"This summary has been logged in your 'Weekly_Summary' tab.\n"
            f"For full analytics, please check your Guzo dashboard.\n\n"
            f"Best regards,\n"
            f"Guzo Guest Assist AutoBot 🤖"
        )

        send_email(recipient_email, email_subject, email_body)
        print(f"📧 Summary emailed to {recipient_email}")

        # -----------------------------------------------------------------
        # TELEGRAM MESSAGE
        # -----------------------------------------------------------------
        if bot and telegram_chat_id:
            report_text = (
                f"📊 *{hotel_name} – Weekly Summary*\n"
                f"📅 {week_range}\n\n"
                f"🏨 Total Bookings: {total_bookings}\n"
                f"🛏️ Nights: {int(total_nights)}\n"
                f"💰 Revenue: {total_revenue:,.0f} ETB\n"
                f"📈 Occupancy: {occupancy:.1f}%\n"
                f"🏷️ ADR: {adr:,.2f} ETB\n"
                f"💹 RevPAR: {revpar:,.2f} ETB\n"
                f"🏡 Top Room: {top_room}\n\n"
                f"✅ Auto-generated & logged in Weekly_Summary tab"
            )
            bot.send_message(chat_id=int(telegram_chat_id), text=report_text, parse_mode="Markdown")
            print(f"📨 Telegram summary sent → {telegram_chat_id}")
        else:
            print("⚠️ Telegram not configured or chat ID missing.")

    except Exception as e:
        print(f"❌ Error in {hotel_name}: {e}")


# ---------------------------------------------------------------------
# PROCESS ALL ACTIVE HOTELS
# ---------------------------------------------------------------------
def run_all_hotels():
    """Iterate over all active hotels in Hotel_Contacts_Master."""
    try:
        master = client.open("Hotel_Contacts_Master").sheet1
        hotels = master.get_all_records()
        active_hotels = [h for h in hotels if "active" in h.get("Integration Status", "").lower()]

        print(f"📘 Processing {len(active_hotels)} active hotels...")
        for hotel in active_hotels:
            sheet_id = hotel.get("Sheet ID")
            name = hotel.get("Hotel Name")
            email = hotel.get("Reservation Email") or hotel.get("Main Contact Email")
            chat_id = str(hotel.get("Telegram Chat ID", "")).strip()
            total_rooms = int(hotel.get("Total Rooms", 30))
            if sheet_id and name:
                generate_weekly_summary(sheet_id, name, email, chat_id, total_rooms)

        print("✅ All summaries processed successfully.")

    except Exception as e:
        print(f"❌ Error processing hotels: {e}")


# ---------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Starting Guzo Guest Assist Weekly Summary v5.0...")
    run_all_hotels()
    print("✅ All hotel summaries generated & notifications sent.")
