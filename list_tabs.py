from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Path to your service account file
SERVICE_ACCOUNT_FILE = "creds/guzo_service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Your spreadsheet ID
SPREADSHEET_ID = "1UO3G840GtNseCRt2C_JsifFNXbK8w8Taksw6hd2dLAI"

def list_tabs():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()

    print("Tabs in this spreadsheet:")
    for sheet in spreadsheet.get("sheets", []):
        print("-", sheet["properties"]["title"])

if __name__ == "__main__":
    list_tabs()
