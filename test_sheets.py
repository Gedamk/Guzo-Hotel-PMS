# test_sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from guzo_booking_bot.modules.google_sheets import SPREADSHEET_GUEST_ASSIST_ID, SPREADSHEET_HOTEL_CONTACTS_ID

def test_google_sheets_access():
    # Define scope
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]

    # Load credentials
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    except FileNotFoundError:
        print("Ã¢ÂÂ credentials.json not found. Make sure it exists in the project root.")
        return

    client = gspread.authorize(creds)
    print("Ã¢ÂÂ Successfully authenticated with Google Sheets.")

    # Function to test a single spreadsheet
    def test_sheet(spreadsheet_id, sheet_name):
        try:
            sheet = client.open_by_key(spreadsheet_id).sheet1
            records = sheet.get_all_records()
            print(f"Ã¢ÂÂ {sheet_name} Sheet Access Success!")
            print(f"Found {len(records)} records.")
            for r in records[:5]:  # print first 5 rows
                print(r)
        except gspread.SpreadsheetNotFound:
            print(f"Ã¢ÂÂ Spreadsheet not found: {sheet_name}. Check your spreadsheet ID and sharing settings.")
        except gspread.exceptions.APIError as e:
            print(f"Ã¢ÂÂ API error accessing {sheet_name}: {e}")

    # Test GuestAssist sheet
    test_sheet(SPREADSHEET_GUEST_ASSIST_ID, "GuestAssist")

    # Test HotelContacts sheet
    test_sheet(SPREADSHEET_HOTEL_CONTACTS_ID, "HotelContacts")


if __name__ == "__main__":
    test_google_sheets_access()
