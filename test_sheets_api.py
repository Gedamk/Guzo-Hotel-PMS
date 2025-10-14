from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

# 🔑 Path to your service account key
creds_path = r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json"

# 🔒 Google Sheets read-only scope
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

try:
    # ✅ Build credentials
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=scopes
    )

    # ✅ Build the Sheets API service
    service = build("sheets", "v4", credentials=creds)

    print("🔍 Testing Sheets API connection...")

    # 🧾 Replace with your actual Sheet ID (from the URL)
    SAMPLE_SPREADSHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
    SAMPLE_RANGE_NAME = "A1:D5"

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )

    rows = result.get("values", [])
    if not rows:
        print("⚠️ No data found or you need to share the Sheet with your service account.")
    else:
        print("✅ Sheets API working! Here's a preview:")
        for row in rows:
            print(row)

except FileNotFoundError:
    print("❌ Error: Service account JSON file not found.")
except HttpError as e:
    print("❌ Google API returned an error:")
    print(e)
except Exception as e:
    print("⚠️ Unexpected error occurred:")
    print(e)
