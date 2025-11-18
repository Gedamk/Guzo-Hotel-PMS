# -*- coding: utf-8 -*-
"""
auto_welcome_trigger.py – Guzo Guest Assist
-------------------------------------------
Automatically detects new hotels in the Hotel_Contacts_Master Google Sheet
and sends bilingual welcome emails using send_welcome_email.py.
"""

import os
import datetime
from dotenv import load_dotenv
from guzo_backend.modules.google_sheets import init_client
from guzo_backend.send_welcome_email import send_welcome_email

# ✅ Explicitly load environment variables from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))


def run_auto_welcome():
    """Scan the Google Sheet for new hotels and send welcome emails."""
    print("[START] Checking for new hotels...")

    # Initialize Google Sheets client
    client = init_client()
    sheet_id = os.getenv("HOTEL_CONTACT_SHEET_ID")

    if not sheet_id:
        print("❌ ERROR: HOTEL_CONTACT_SHEET_ID not found in environment variables.")
        return

    # Open the master contact sheet
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet("Hotel_Contacts_Master")

    # Fetch all rows
    rows = worksheet.get_all_values()
    if len(rows) <= 1:
        print("[WARN] No hotel data found in the sheet.")
        return

    # Column index mapping (0-based)
    HOTEL_NAME_COL = 0      # Hotel Name
    EMAIL_COL = 4           # Main Contact Email
    STATUS_COL = 11         # Integration Status
    LAST_SENT_COL = 12      # Last Welcome Email Sent (Column M)

    # Skip header and process rows
    for i, row in enumerate(rows[1:], start=2):
        try:
            hotel_name = row[HOTEL_NAME_COL].strip() if len(row) > HOTEL_NAME_COL else ""
            recipient_email = row[EMAIL_COL].strip() if len(row) > EMAIL_COL else ""
            status = row[STATUS_COL].strip() if len(row) > STATUS_COL else ""
            last_sent = row[LAST_SENT_COL].strip() if len(row) > LAST_SENT_COL else ""

            # Validation & logic
            if not hotel_name or not recipient_email:
                continue
            if status.lower() != "active":
                continue
            if last_sent:
                continue

            print(f"[INFO] Sending welcome email to {hotel_name} ({recipient_email})...")
            send_welcome_email(hotel_name, recipient_email)

            # Log sending date
            today = datetime.date.today().strftime("%Y-%m-%d")
            worksheet.update_acell(f"M{i}", today)

            print(f"[OK] Welcome email logged for {hotel_name}")

        except Exception as e:
            print(f"[ERROR] Row {i}: {e}")

    print("[DONE] Auto Welcome Email Check completed.")


if __name__ == "__main__":
    run_auto_welcome()
