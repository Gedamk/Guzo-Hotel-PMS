"""
sheets_config.py
-----------------
Central configuration for all Google Sheets in Guzo Guest Assist project.
"""

import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread

# Load environment
load_dotenv()

# Credentials
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
client = gspread.authorize(creds)

# Sheet URLs from .env
SHEETS = {
    "guest_assist": os.getenv("GUEST_ASSIST_SHEET"),
    "hotel_contact": os.getenv("HOTEL_CONTACT_SHEET"),
    "notification_log": os.getenv("NOTIFICATION_LOG_SHEET"),
}

# Test access
for name, url in SHEETS.items():
    try:
        sheet = client.open_by_url(url)
        print(f"Ã¢ÂÂ Connected to {name}: {sheet.title}")
    except Exception as e:
        print(f"Ã¢ÂÂ Failed to connect to {name}: {e}")
