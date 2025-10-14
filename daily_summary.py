# -*- coding: utf-8 -*-
"""
Daily Summary ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Guzo Guest Assist
Summarizes today's new bookings from Google Sheet
and emails a short report via SendGrid.
"""

import os, datetime as dt
import gspread
import pandas as pd
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from log_helper import log_event

load_dotenv(r"C:\Users\Gedan\Desktop\Guzo\.env")

GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SG_API = os.getenv("SENDGRID_API_KEY")
FROM = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
TO = os.getenv("TO_EMAIL", "manager@guzoassist.com")

def main():
    try:
        sa = gspread.service_account(CREDS)
        ws = sa.open_by_key(GA_ID).sheet1
        df = pd.DataFrame(ws.get_all_records())

        if df.empty:
            log_event("Daily Summary", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Success", "No new data found")
            print("No data in sheet. Exiting.")
            return

        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        today = dt.date.today()
        df_today = df[df["Timestamp"].dt.date == today]

        if df_today.empty:
            log_event("Daily Summary", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Success", "No bookings today.")
            print("No bookings today.")
            return

        total = len(df_today)
        hotels = df_today["Hotel Name"].nunique()
        revenue = df_today["Revenue"].sum() if "Revenue" in df_today else 0

        summary = f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Daily Summary for {today}\n\n" \
                  f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ÃÂÃÂÃÂÃÂ¾ Total Bookings: {total}\nÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Hotels Involved: {hotels}\nÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ° Estimated Revenue: ${revenue:,.2f}\n"

        sg = SendGridAPIClient(SG_API)
        email = Mail(from_email=FROM, to_emails=TO,
                     subject=f"[Guzo Reports] Daily Summary {today}",
                     plain_text_content=summary)
        resp = sg.send(email)

        log_event("Daily Summary", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Success", f"Sent {total} bookings summary, status {resp.status_code}")
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Daily report sent successfully.")

    except Exception as e:
        log_event("Daily Summary", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed", str(e))
        raise

if __name__ == "__main__":
    main()
