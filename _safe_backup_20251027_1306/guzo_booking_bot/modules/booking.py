# guzo_booking_bot/modules/booking.py
"""
Booking Module
- Google Sheets connection
- Logs and syncs bookings
- Resets sheet for testing
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from guzo_booking_bot import config as cfg

HEADER = [
    "Hotel Name", "Guest Name", "Check-in", "Check-out",
    "Room", "Source", "Contact", "Status", "Timestamp"
]

def get_sheet():
    """Authenticate and return main booking sheet"""
    creds = Credentials.from_service_account_file(
        cfg.SERVICE_ACCOUNT_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(cfg.SPREADSHEET_GUEST_ASSIST_ID)
    return sheet.sheet1

def reset_sheet():
    """Clear and reset booking sheet with headers"""
    ws = get_sheet()
    ws.clear()
    ws.append_row(HEADER)
    print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Booking sheet reset complete.")

def log_booking(hotel_name, guest_name, check_in, check_out,
                room, source, contact="", status="Pending", timestamp=None):
    """Append a single booking to sheet"""
    ws = get_sheet()
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [hotel_name, guest_name, check_in, check_out,
           room, source, contact, status, timestamp]
    ws.append_row(row)
    print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Booking logged: {guest_name} at {hotel_name}")

def sync_bookings(bookings_list):
    """Bulk sync multiple bookings"""
    ws = get_sheet()
    for booking in bookings_list:
        row = [booking.get(h, "") for h in HEADER]
        ws.append_row(row)
    print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {len(bookings_list)} bookings synced")
