# -*- coding: utf-8 -*-
"""
add_hotel_to_google_sheet.py – Central registry sync for Guzo Guest Assist
--------------------------------------------------------------------------
Logs newly registered hotels to Google Sheets (Hotel_Contacts_Master → Hotels)
and ensures no duplication.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from guzo_booking_bot.modules.log_helper import log_event

# ✅ Your actual Google Sheet details (Hotel_Contacts_Master)
SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
TAB_NAME = "Hotels"

def add_hotel_to_google_sheet(hotel: dict):
    """
    Safely adds a new hotel to the Google Sheet registry.
    Avoids duplicate entries based on Telegram Chat ID.
    """
    try:
        # Authenticate using your service account credentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_booking_bot/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        print("✅ Successfully authenticated with Google Sheets.")

        # Open the main sheet and select tab
        sheet = client.open_by_key(SHEET_ID).worksheet(TAB_NAME)
        rows = sheet.get_all_records()

        # Prevent duplicates
        for row in rows:
            if str(row.get("telegram_chat_id", "")) == str(hotel["telegram_chat_id"]):
                print(f"↩️ Hotel already exists in Google Sheet: {hotel['name']}")
                log_event("GoogleSheetsSync", "SKIPPED", f"Duplicate entry: {hotel['name']}")
                return

        # New entry
        new_row = [
            hotel.get("id", ""),
            hotel.get("name", ""),
            hotel.get("city", ""),
            hotel.get("email", ""),
            hotel.get("telegram_chat_id", ""),
            hotel.get("sheet_id", ""),
            hotel.get("phone", ""),
            hotel.get("registered_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ]

        # Append the row
        sheet.append_row(new_row)
        print(f"✅ Added {hotel['name']} to Google Sheet registry")
        print(f"☁️ Synced {hotel['name']} to Google Sheets successfully.")
        log_event("GoogleSheetsSync", "SUCCESS", f"✅ Added {hotel['name']} to Google Sheet registry")

    except Exception as e:
        print(f"❌ Google Sheets sync failed: {e}")
        log_event("GoogleSheetsSync", "ERROR", f"❌ Failed to sync {hotel.get('name')} | {e}")
