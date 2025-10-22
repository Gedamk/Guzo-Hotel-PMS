# -*- coding: utf-8 -*-
"""
test_google_sheet.py – Guzo Guest Assist (Final Auto-Fix Version)
-----------------------------------------------------------------
Quick live test to read/write Google Sheet data using gspread + service account.
Includes automatic path correction for credentials and clean debug output.
"""

import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# ======================================================
# 🔧 LOAD ENVIRONMENT VARIABLES
# ======================================================
load_dotenv()

# Fetch paths from .env or apply fallback
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID_GUZO_TEST")

# ✅ Auto-correct known fallback issue on Windows
if not CREDENTIALS_PATH or not os.path.exists(CREDENTIALS_PATH):
    corrected_path = "C:/Users/Gedan/Desktop/Guzo/guzo_booking_bot/creds/guzo_service_account.json"
    if os.path.exists(corrected_path):
        print("⚙️  Auto-fix applied → Corrected credentials path.")
        CREDENTIALS_PATH = corrected_path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = corrected_path
    else:
        print("❌ Credentials file not found at expected fallback location:")
        print("   ", corrected_path)

# ======================================================
# 📄 CONNECT TO GOOGLE SHEET
# ======================================================
def connect_to_google_sheet():
    """Connect to Google Sheets using the service account credentials."""
    if not CREDENTIALS_PATH:
        raise FileNotFoundError("❌ GOOGLE_APPLICATION_CREDENTIALS not set or invalid in .env")

    print(f"🔍 Debug: Using credentials → {CREDENTIALS_PATH}")

    if not os.path.isfile(CREDENTIALS_PATH):
        raise FileNotFoundError(f"❌ Google credentials JSON not found at: {CREDENTIALS_PATH}")

    # Define API access scopes
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet("TestData")
    print("✅ Connected to Google Sheet successfully.")
    return sheet


# ======================================================
# 🧪 WRITE + VERIFY TEST ENTRY
# ======================================================
def write_test_entry():
    """Append a test row with timestamp and verify the connection."""
    sheet = connect_to_google_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, "Guzo Guest Assist", "✅ Connection OK"]

    sheet.append_row(row)
    print("✅ Successfully wrote test row to Google Sheet.")

    # Display last few entries for confirmation
    records = sheet.get_all_values()
    print("\n📊 Last entries:")
    for r in records[-5:]:
        print("  ", r)


# ======================================================
# 🚀 MAIN ENTRY POINT
# ======================================================
if __name__ == "__main__":
    try:
        write_test_entry()
    except Exception as e:
        print(f"❌ Error during Google Sheet test: {e}")
