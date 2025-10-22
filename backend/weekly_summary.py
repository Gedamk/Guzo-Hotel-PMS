# -*- coding: utf-8 -*-
"""
weekly_summary.py – Guzo Guest Assist v11.6
--------------------------------------------
Generates weekly summary reports for all partner hotels.
Fetches Google Sheets data → processes by week → sends both
plain text and branded HTML email summaries.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ UTF-8 fix for Windows output
sys.stdout.reconfigure(encoding="utf-8")

# ======================================================
# 🌍 ENVIRONMENT SETUP
# ======================================================
load_dotenv(override=True)
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
EMAIL_TO = os.getenv("TO_EMAIL")
EMAIL_FROM = os.getenv("FROM_EMAIL")
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")

# ======================================================
# 📊 GOOGLE SHEETS CONNECTION
# ======================================================
def load_hotels():
    """Load hotel config file with sheet IDs."""
    path = os.path.join("backend", "config", "config_hotels.json")
    if not os.path.exists(path):
        print(f"❌ Missing config file: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("HOTELS", [])


def connect_to_sheet(sheet_id):
    """Open a Google Sheet using the service account."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError("❌ Google credentials JSON not found!")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).sheet1


# ======================================================
# 🧾 MAIN LOGIC
# ======================================================
def summarize_hotel(sheet_id, name, monday, sunday):
    """Fetch and summarize data for one hotel."""
    try:
        sheet = connect_to_sheet(sheet_id)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if "Date" not in df.columns:
            raise KeyError("Date")

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        mask = (df["Date"] >= monday) & (df["Date"] <= sunday)
        week_df = df.loc[mask]

        if week_df.empty:
            return f"⚠️ No data for {name} in week {monday.isocalendar()[1]}."

        total_rev = week_df["Revenue"].sum() if "Revenue" in week_df.columns else 0
        return f"🏨 {name}: {len(week_df)} entries – Total Revenue ${total_rev:,.2f}"
    except Exception as e:
        return f"❌ Error for {name}: {e}"


# ======================================================
# ✉️ BASIC TEXT EMAIL (for compatibility)
# ======================================================
def send_email_report(summary_text):
    """Send the plain-text version of the summary."""
    if not SENDGRID_KEY:
        print("❌ Missing SENDGRID_API_KEY.")
        return
    try:
        sg = SendGridAPIClient(SENDGRID_KEY)
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=EMAIL_TO,
            subject="[Guzo Reports] Weekly Summary (Plain Text)",
            html_content=f"<pre>{summary_text}</pre>",
        )
        sg.send(message)
        print(f"✅ Plain-text summary email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"❌ Failed to send plain-text email: {e}")


# ======================================================
# 🖼️ BRANDED HTML EMAIL
# ======================================================
def send_html_email(summaries, week_num, monday, sunday):
    """Send a formatted HTML email with table results using SendGrid."""
    template_path = os.path.join("backend", "email_templates", "weekly_report.html")
    if not os.path.exists(template_path):
        print(f"❌ Missing HTML template: {template_path}")
        return

    with open(template_path, "r", encoding="utf-8") as f:
        html_template = f.read()

    # Build table rows dynamically
    table_rows = ""
    for item in summaries:
        if "❌" in item:
            status_class = "error"
        elif "⚠️" in item:
            status_class = "warning"
        else:
            status_class = "success"

        hotel_name = item.split(":")[0].replace("🏨", "").strip()
        details = item.split(":", 1)[1].strip() if ":" in item else item

        table_rows += f"""
        <tr>
          <td>{hotel_name}</td>
          <td class="{status_class}">{status_class.title()}</td>
          <td>{details}</td>
        </tr>
        """

    html_content = (
        html_template
        .replace("{{ table_rows }}", table_rows)
        .replace("{{ week_range }}", f"Week {week_num} ({monday:%b %d} → {sunday:%b %d})")
        .replace("{{ generated_time }}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    if not SENDGRID_KEY:
        print("❌ SENDGRID_API_KEY missing — cannot send HTML email.")
        return

    try:
        sg = SendGridAPIClient(SENDGRID_KEY)
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=EMAIL_TO,
            subject=f"[Guzo Reports] Weekly Summary – Week {week_num}",
            html_content=html_content,
        )
        sg.send(message)
        print(f"✅ Branded HTML email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"❌ Failed to send HTML email: {e}")


# ======================================================
# 🚀 MAIN EXECUTION
# ======================================================
if __name__ == "__main__":
    print("📊 Running in Test mode")

    try:
        hotels = load_hotels()
        if not hotels:
            print("❌ No hotel configuration found.")
            sys.exit(1)

        today = datetime.now()
        monday = today - timedelta(days=today.weekday() + 7)
        sunday = monday + timedelta(days=6)
        week_num = monday.isocalendar()[1]

        print(f"🧩 Using credentials: {CREDENTIALS_PATH}")
        print(f"🧩 Running for LAST week → Year {today.year}, Week {week_num}")
        print(f"📅 Reporting range: {monday.date()} → {sunday.date()}")

        summaries = []
        for h in hotels:
            print(f"🏨 Processing {h['name']}...")
            print(f"   ↳ Sheet ID: {h['sheet_id']}")
            result = summarize_hotel(h["sheet_id"], h["name"], monday, sunday)
            summaries.append(result)
            print(result)

        # Combine results
        full_summary = "\n".join(summaries)

        # Send both plain text and HTML reports
        send_email_report(full_summary)
        send_html_email(summaries, week_num, monday, sunday)

        print("[{0}] Weekly Summary: ✅ Success - All reports sent.".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        print("✅ Weekly Multi-Hotel Reports completed successfully.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
