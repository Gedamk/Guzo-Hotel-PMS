# -*- coding: utf-8 -*-
"""
hotel_directory.py
--------------------------------------------
Fetches live hotel contact information from Google Sheets.
Used by Guzo Guest Assist bot for multi-channel communication.
"""

import os
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# 🔑 Path to your service account key
creds_path = r"C:\Users\Gedan\Desktop\Guzo\guzo_backend\creds\guzo_service_account.json"

# 🧾 Google Sheets details (update your own Sheet ID below)
SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
SHEET_RANGE = "A1:L100"  # adjust columns if you added Telegram/Viber/etc.

# 🔒 Scopes for read-only access
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def fetch_hotel_data():
    """Fetch all hotel contact data from Google Sheets."""
    try:
        # Build credentials and API service
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)

        print("🔍 Fetching hotel contacts from Google Sheets...")

        # Request data
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SHEET_ID, range=SHEET_RANGE)
            .execute()
        )

        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            print("⚠️ No hotel data found or empty sheet.")
            return pd.DataFrame()

        # Convert to DataFrame
        headers = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)

        print(f"✅ Loaded {len(df)} hotels from sheet.")
        return df

    except Exception as e:
        print(f"❌ Error loading hotel contacts: {e}")
        return pd.DataFrame()


# 🧪 Optional: Test the function directly
if __name__ == "__main__":
    hotels = fetch_hotel_data()
    if not hotels.empty:
        print(hotels.head())
