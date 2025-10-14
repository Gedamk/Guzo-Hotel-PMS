"""
test_read_sheets.py
--------------------------------
Checks actual access to your Google Sheets.
Lists all worksheets and prints first few rows.
"""

import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Load environment
load_dotenv()

# Get creds file path
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
print(f"Ã°ÂÂÂ Using credentials: {creds_path}")

# Define scope
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
client = gspread.authorize(creds)

# Ã°ÂÂÂ Replace this with your actual Google Sheet URL
TEST_SHEET_URL = "https://docs.google.com/spreadsheets/d/your-sheet-id-here"

try:
    sheet = client.open_by_url(TEST_SHEET_URL)
    worksheet = sheet.sheet1
    print(f"Ã°ÂÂÂ Sheet title: {worksheet.title}")
    print("Ã°ÂÂÂ First 5 rows:")
    for row in worksheet.get_all_values()[:5]:
        print(row)
    print("Ã¢ÂÂ Successfully read data from Google Sheets!")
except Exception as e:
    print(f"Ã¢ÂÂ Error reading sheet: {e}")
