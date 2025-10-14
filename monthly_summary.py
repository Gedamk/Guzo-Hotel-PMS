# -*- coding: utf-8 -*-
"""
Monthly Summary Ã¢ÂÂ Guzo Guest Assist
Aggregates last 30 days bookings and emails performance summary.
"""

import os, datetime as dt
import gspread, pandas as pd
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from log_helper import log_event

load_dotenv(r"C:\Users\Gedan\Desktop\Guzo\.env")

GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SG_API = os.getenv("SENDGRID_API_KEY")
FROM = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
TO = os.getenv("TO_EMAIL", "owner@guzoassist.com")

def main():
    try:
        sa = gspread.service_account(CREDS)
        ws = sa.open_by_key(GA_ID).sheet1
        df = pd.DataFrame(ws.get_all_records())

        if df.empty:
            log_event("Monthly Summary", "Ã¢ÂÂ Success", "No data found.")
            print("No data in Guest Assist.")
            return

        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        start_date = dt.date.today() - dt.timedelta(days=30)
        df_recent = df[df["Timestamp"].dt.date >= start_date]

        if df_recent.empty:
            log_event("Monthly Summary", "Ã¢ÂÂ Success", "No recent bookings.")
            print("No recent bookings.")
            return

        # KPIs
        total_bookings = len(df_recent)
        unique_hotels = df_recent["Hotel Name"].nunique()
        revenue = df_recent["Revenue"].sum() if "Revenue" in df_recent else 0
        avg_per_day = total_bookings / 30

        summary = (
            f"Ã°ÂÂÂ Monthly Performance (last 30 days)\n\n"
            f"Ã°ÂÂÂ¨ Active Hotels: {unique_hotels}\n"
            f"Ã°ÂÂ§Â¾ Total Bookings: {total_bookings}\n"
            f"Ã°ÂÂÂ° Total Revenue: ${revenue:,.2f}\n"
            f"Ã°ÂÂÂ Avg. Bookings per Day: {avg_per_day:.1f}\n\n"
            f"Ã¢ÂÂ Guzo Guest Assist Automated System"
        )

        sg = SendGridAPIClient(SG_API)
        email = Mail(from_email=FROM, to_emails=TO,
                     subject="[Guzo Reports] Monthly Performance Summary",
                     plain_text_content=summary)
        resp = sg.send(email)

        log_event("Monthly Summary", "Ã¢ÂÂ Success", f"Report sent, status {resp.status_code}")
        print("Ã¢ÂÂ Monthly report sent successfully.")

    except Exception as e:
        log_event("Monthly Summary", "Ã¢ÂÂ Failed", str(e))
        raise

if __name__ == "__main__":
    main()
