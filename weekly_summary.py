# -*- coding: utf-8 -*-
"""
Smart Revenue Trend Report (with Action Summary) Ã¢ÂÂ Guzo Guest Assist
--------------------------------------------------------------------
Generates weekly revenue, occupancy, and trend analysis for all hotels.
- Compares current week vs previous week
- Creates "Top 3 Action Recommendations"
- Supports ETB + USD view
- Sends PDF + email via SendGrid
"""

import os
import io
import datetime as dt
from dotenv import load_dotenv
import gspread
import pandas as pd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from log_helper import log_event

# --- SETTINGS ---
import os
from dotenv import load_dotenv

# Ã¢ÂÂ Auto-select environment file based on mode
ENV_FILE = ".env.production" if os.getenv("MODE") == "production" else ".env"
load_dotenv(os.path.join(r"C:\Users\Gedan\Desktop\Guzo", ENV_FILE))

print(f"Ã°ÂÂÂ Running in {'Production' if ENV_FILE == '.env.production' else 'Test'} mode")

BASE = os.path.dirname(__file__)
REPORTS_DIR = os.path.join(BASE, "reports")

SG_API = os.getenv("SENDGRID_API_KEY")
FROM = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
TO = os.getenv("TO_EMAIL", "owner@guzoassist.com")
SUBJ_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[Guzo Reports]")
GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
HC_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS")
CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

ETB_TO_USD = 0.017  # optional conversion for international revenue tracking

# --- HELPERS ---
def iso_year_week(d: dt.date):
    y, w, _ = d.isocalendar()
    return y, w

def start_end_of_iso_week(year: int, week: int):
    monday = dt.date.fromisocalendar(year, week, 1)
    sunday = dt.date.fromisocalendar(year, week, 7)
    return monday, sunday

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path

def read_ws(sa, sh_id):
    return pd.DataFrame(sa.open_by_key(sh_id).sheet1.get_all_records())

# --- LOAD DATA ---
def load_all_frames():
    sa = gspread.service_account(CREDS)
    df_guest = read_ws(sa, GA_ID)
    df_hotel = read_ws(sa, HC_ID)
    return df_guest, df_hotel

# --- WEEKLY DATA CALCULATION ---
def compute_weekly_data(df_guest, df_hotel, year, week):
    start, end = start_end_of_iso_week(year, week)
    df_guest["Timestamp"] = pd.to_datetime(df_guest["Timestamp"], errors="coerce")
    df_week = df_guest[(df_guest["Timestamp"].dt.date >= start) & (df_guest["Timestamp"].dt.date <= end)].copy()

    if df_week.empty:
        return pd.DataFrame()

    df_week["Room Nights"] = pd.to_numeric(df_week.get("Room Nights", 0), errors="coerce").fillna(0)
    df_week["Rate per Night (ETB)"] = pd.to_numeric(df_week.get("Rate per Night (ETB)", 0), errors="coerce").fillna(0)
    df_week["Revenue (ETB)"] = df_week["Room Nights"] * df_week["Rate per Night (ETB)"]

    result = []
    for hotel, group in df_week.groupby("Hotel Name"):
        total_rooms = df_hotel.loc[df_hotel["Hotel Name"] == hotel, "Total Rooms"].squeeze()
        total_rooms = total_rooms if pd.notna(total_rooms) else 20
        rn = group["Room Nights"].sum()
        rev = group["Revenue (ETB)"].sum()
        adr = rev / rn if rn > 0 else 0
        occ = (rn / (total_rooms * 7) * 100) if total_rooms else None
        revpar = (rev / (total_rooms * 7)) if total_rooms else None
        result.append({
            "Hotel": hotel,
            "Room Nights": rn,
            "Revenue": rev,
            "ADR": adr,
            "Occupancy%": occ,
            "RevPAR": revpar
        })
    return pd.DataFrame(result)

# --- COMPARE WEEKS + INSIGHTS ---
def compare_weeks(curr, prev):
    if curr.empty:
        return curr, []

    insights = []
    for i, row in curr.iterrows():
        hotel = row["Hotel"]
        prev_row = prev[prev["Hotel"] == hotel]
        if not prev_row.empty:
            p = prev_row.iloc[0]
            rev_change = ((row["Revenue"] - p["Revenue"]) / p["Revenue"] * 100) if p["Revenue"] > 0 else 0
            occ_change = ((row["Occupancy%"] - p["Occupancy%"]) if p["Occupancy%"] else 0)
            adr_change = ((row["ADR"] - p["ADR"]) / p["ADR"] * 100) if p["ADR"] > 0 else 0

            trend = "Ã¢Â¬ÂÃ¯Â¸Â Growth" if rev_change > 5 else ("Ã¢Â¬ÂÃ¯Â¸Â Decline" if rev_change < -5 else "Ã¢ÂÂ¡Ã¯Â¸Â Stable")
            comment = f"{trend}: Revenue {rev_change:+.1f}%, ADR {adr_change:+.1f}%, Occ {occ_change:+.1f} pts."

            # Tailored suggestions
            if rev_change < -10:
                comment += " Ã¢ÂÂ  Focus on weekday bookings or flash promotions."
            elif rev_change > 10:
                comment += " Ã°ÂÂÂ° Excellent growth Ã¢ÂÂ keep current pricing strategy."
            elif occ_change < -5:
                comment += " Ã¢ÂÂ  Decline in occupancy Ã¢ÂÂ target local weekend travelers."
        else:
            comment = "New hotel added this week (no previous comparison)."
        insights.append(comment)

    curr["Insight"] = insights
    return curr, insights

# --- GENERATE ACTION SUMMARY ---
def generate_summary(df):
    if df.empty:
        return ["No bookings to analyze."]
    top_grower = df.loc[df["Revenue"].idxmax(), "Hotel"]
    top_decline = df.loc[df["Revenue"].idxmin(), "Hotel"]
    avg_occ = df["Occupancy%"].mean()

    summary = [
        f"Ã°ÂÂÂ Best performer: {top_grower} Ã¢ÂÂ top revenue earner this week.",
        f"Ã¢ÂÂ  Watchlist: {top_decline} Ã¢ÂÂ lowest revenue; review rates and sales channels.",
        f"Ã°ÂÂÂ Average occupancy across hotels: {avg_occ:.1f}%. Target: 65%+.",
    ]
    # Additional action logic
    if avg_occ < 40:
        summary.append("Ã°ÂÂÂ¡ Action: Launch early-week promotions and group offers.")
    elif avg_occ > 70:
        summary.append("Ã°ÂÂÂ¥ Demand strong Ã¢ÂÂ consider rate increase of 5Ã¢ÂÂ10%.")
    else:
        summary.append("Ã¢ÂÂ Maintain pricing; focus on review responses and guest experience.")

    return summary[:4]

# --- PDF BUILDER ---
def build_pdf(df, meta):
    folder = ensure_dir(os.path.join(REPORTS_DIR, f"{meta['year']}-week{meta['week']:02d}"))
    pdf_path = os.path.join(folder, f"Action_Revenue_Report_{meta['year']}-w{meta['week']:02d}.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # ---- SUMMARY PAGE ----
    elements.append(Paragraph("<b>Guzo Guest Assist Ã¢ÂÂ Weekly Action Revenue Report</b>", styles["Title"]))
    elements.append(Paragraph(f"Week {meta['week']} ({meta['start']} Ã¢ÂÂ {meta['end']})", styles["Normal"]))
    elements.append(Spacer(1, 12))

    summary_points = generate_summary(df)
    elements.append(Paragraph("<b>Top 3 Recommendations:</b>", styles["Heading2"]))
    for s in summary_points:
        elements.append(Paragraph(f"Ã¢ÂÂ¢ {s}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ---- DETAIL PER HOTEL ----
    for _, row in df.iterrows():
        usd = row["Revenue"] * ETB_TO_USD
        elements.append(Paragraph(f"<b>{row['Hotel']}</b>", styles["Heading3"]))
        elements.append(Paragraph(
            f"Revenue: ETB {row['Revenue']:.0f} (~USD {usd:.0f}) | Room Nights: {row['Room Nights']} | "
            f"ADR: {row['ADR']:.0f} | Occupancy: {row['Occupancy%']:.1f}% | RevPAR: {row['RevPAR']:.0f}",
            styles["Normal"]
        ))
        elements.append(Paragraph(f"<i>{row['Insight']}</i>", styles["Italic"]))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    return pdf_path

# --- EMAIL REPORT ---
def email_report(pdf_path, meta):
    sg = SendGridAPIClient(SG_API)
    subject = f"{SUBJ_PREFIX} Action Revenue Report Ã¢ÂÂ Week {meta['week']}"
    body = (
        f"Dear Team,\n\nAttached is the Smart Revenue Action Report for Week {meta['week']} "
        f"({meta['start']} Ã¢ÂÂ {meta['end']}).\nIncludes occupancy, ADR, trends, and actionable insights.\n\n"
        f"Ã¢ÂÂ Guzo Guest Assist System"
    )
    msg = Mail(from_email=FROM, to_emails=TO, subject=subject, plain_text_content=body)
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), filename=os.path.basename(pdf_path))
    sg.send(msg)
    print("Ã¢ÂÂ Action Revenue Report emailed successfully.")

# --- MAIN ---
def main():
    try:
        df_guest, df_hotel = load_all_frames()
        today = dt.date.today()
        y, w, _ = today.isocalendar()
        last_year, last_week = (y, w - 1) if w > 1 else (y - 1, dt.date(y - 1, 12, 28).isocalendar()[1])
        prev_year, prev_week = (y, w - 2) if w > 2 else (y - 1, dt.date(y - 1, 12, 28).isocalendar()[1])

        curr_df = compute_weekly_data(df_guest, df_hotel, last_year, last_week)
        prev_df = compute_weekly_data(df_guest, df_hotel, prev_year, prev_week)
        meta = {
            "year": last_year,
            "week": last_week,
            "start": start_end_of_iso_week(last_year, last_week)[0].isoformat(),
            "end": start_end_of_iso_week(last_year, last_week)[1].isoformat(),
        }

        if curr_df.empty:
            log_event("Action Revenue Report", "Ã¢ÂÂ Success", "No data for last week.")
            print("No data for last week.")
            return

        compared_df, _ = compare_weeks(curr_df, prev_df)
        pdf_path = build_pdf(compared_df, meta)
        email_report(pdf_path, meta)
        log_event("Action Revenue Report", "Ã¢ÂÂ Success", f"Report sent: {pdf_path}")
        print("Ã¢ÂÂ Weekly Action Revenue Report completed successfully.")

    except Exception as e:
        log_event("Action Revenue Report", "Ã¢ÂÂ Failed", str(e))
        raise

if __name__ == "__main__":
    main()
