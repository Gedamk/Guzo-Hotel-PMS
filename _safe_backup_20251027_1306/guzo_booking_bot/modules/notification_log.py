"""
Notification Logger
- Logs notification results (Email, SMS, WhatsApp, Telegram, Viber)
- Stores results in a Google Sheet for dashboard reporting
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging
from guzo_booking_bot import config as cfg

logger = logging.getLogger(__name__)

# -----------------------
# Google Sheets Setup
# -----------------------

NOTIFICATION_HEADER = [
    "Guest Name", "Contact", "Channel", "Status", "Message", "Timestamp"
]

def get_notification_sheet():
    """Return the Google Sheet worksheet for notifications."""
    try:
        creds = Credentials.from_service_account_file(
            cfg.GOOGLE_CREDS_FILE,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(cfg.NOTIFICATION_SHEET_ID)
        ws = sheet.sheet1
        # Ensure header exists
        if ws.row_count == 0 or ws.cell(1, 1).value != "Guest Name":
            ws.clear()
            ws.append_row(NOTIFICATION_HEADER)
        return ws
    except Exception as e:
        logger.error(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to authenticate Notification Sheet: {e}")
        raise


# -----------------------
# Core Function
# -----------------------

def log_notification(guest_name: str, contact: str, channel: str, status: str, message: str = ""):
    """
    Log a notification attempt to Google Sheets.
    guest_name : Guest Name
    contact    : Email / Phone / Chat ID
    channel    : Email, SMS, WhatsApp, Telegram, Viber
    status     : SUCCESS / FAILED
    message    : Optional error or success details
    """
    try:
        ws = get_notification_sheet()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [guest_name, contact, channel, status, message, timestamp]
        ws.append_row(row)
        logger.info(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Notification logged: {guest_name} | {contact} | {channel} | {status}")
    except Exception as e:
        logger.error(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to log notification: {e}")
