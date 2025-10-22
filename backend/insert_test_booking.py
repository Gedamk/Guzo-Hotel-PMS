# -*- coding: utf-8 -*-
"""
insert_test_booking.py
------------------------------------------------------------
Quick utility to insert a sample test booking into Sofi Hotel
Google Sheet to verify weekly_summary.py works end-to-end.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ======================================================
# �� Google Sheets credentials
# ======================================================
CREDENTIALS_PATH = r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json"

# Sofi Hotel sheet ID
SHEET_ID = "1YltAe8EAo5LGDt5r5PnrbU9RmE8TS8no8ryd5-3vxb8"

# ======================================================
# �� Authorize & connect
# ======================================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).sheet1  # assumes first tab is Bookings

# ======================================================
# �� Prepare test booking row
# ======================================================
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

test_row = [
    now,                                # Timestamp
    "John Doe",                         # Guest Name
    "Direct",                           # Source
    "2025-10-16",                       # Check-In Date (this week)
    2,                                  # Nights
    "Deluxe Room",                      # Room Type
    1800,                               # Rate Per Night(ETB)
    3600,                               # Revenue(ETB)
    "Confirmed",                        # Booking Status
    "TEST-001",                         # Channel Ref
    "Test booking entry for system check",  # Remark
    "✅ Sent",                          # Auto Reply
    "GuzoBot"                           # Handled By
]

# ======================================================
# ✏️ Insert to Google Sheet
# ======================================================
sheet.append_row(test_row, value_input_option="USER_ENTERED")
print("✅ Test booking added successfully to Sofi Hotel sheet!")


