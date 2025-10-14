import os
from dotenv import load_dotenv

# Load .env file from current directory
load_dotenv()

print("Ã¢ÂÂ Checking environment variables...")
print("Guest Assist ID:", os.getenv("SPREADSHEET_GUEST_ASSIST_ID"))
print("Hotel Contacts ID:", os.getenv("SPREADSHEET_HOTEL_CONTACTS_ID"))
print("Notifications Log ID:", os.getenv("SPREADSHEET_NOTIFICATIONSLOG_ID"))
print("Service Account File:", os.getenv("SERVICE_ACCOUNT_FILE"))
