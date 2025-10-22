# -*- coding: utf-8 -*-
"""
verify_hotel_sheets.py
---------------------------------------
Checks all hotel sheets listed in your Google Sheets contact list
to confirm that:
1. The spreadsheet exists.
2. The 'Bookings' worksheet exists.
3. The correct header row is present.
"""

import os
import gspread
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env", override=True)

CREDENTIALS_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json"
)
CONTACT_SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"  # 👈 replace this later

EXPECTED_HEADERS = [
    "Timestamp", "Guest Name", "Source", "Check-In Date", "Nights",
    "Room Type", "Rate Per Night(ETB)", "Revenue(ETB)", "Booking Status",
    "Channel Ref", "Remark", "Auto Reply", "Handled By"
]

def main():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ Missing credentials file at {CREDENTIALS_PATH}")
        return

    sa = gspread.service_account(filename=CREDENTIALS_PATH)
    try:
        # Open the Hotel Contact List sheet
        contact_sheet = sa.open_by_key(CONTACT_SHEET_ID).sheet1
        hotels = contact_sheet.get_all_records()

        print(f"🏨 Checking {len(hotels)} hotel spreadsheets...\n")

        for hotel in hotels:
            name = hotel.get("Hotel Name")
            sheet_id = hotel.get("Sheet ID")

            if not sheet_id:
                print(f"⚠️  {name}: Missing Sheet ID.")
                continue

            try:
                doc = sa.open_by_key(sheet_id)
                ws = doc.worksheet("Bookings")
                headers = ws.row_values(1)

                if headers == EXPECTED_HEADERS:
                    print(f"✅ {name}: 'Bookings' tab found and header row matches.")
                else:
                    print(f"⚠️  {name}: Header mismatch or missing columns.")
                    print(f"   Found: {headers}")
            except gspread.exceptions.WorksheetNotFound:
                print(f"❌ {name}: Missing 'Bookings' tab.")
            except Exception as e:
                print(f"❌ {name}: Error accessing sheet → {e}")

    except Exception as e:
        print(f"❌ Could not open contact list: {e}")

if __name__ == "__main__":
    main()
