# -*- coding: utf-8 -*-
"""
Google Sheets Module
--------------------
Handles interactions with Google Sheets for bookings, hotel contacts, and notifications.
Now includes local SQLite fallback for failed logs.
"""

import os
import gspread
import sqlite3
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Centralized config (.env is loaded in config.py)
from guzo_booking_bot import config

# === GOOGLE SHEETS CONFIGURATION ===
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

CREDS_FILE = config.GOOGLE_CREDS
SPREADSHEET_GUEST_ASSIST_ID = config.SPREADSHEET_GUEST_ASSIST_ID
SPREADSHEET_HOTEL_CONTACTS_ID = config.SPREADSHEET_HOTEL_CONTACTS_ID
SPREADSHEET_NOTIFICATIONSLOG_ID = config.SPREADSHEET_NOTIFICATIONSLOG_ID

client = None

# === LOCAL SQLITE FALLBACK ===
LOCAL_DB = os.path.join("storage", "logs.db")

def init_local_db():
    """Ensure SQLite fallback exists."""
    os.makedirs("storage", exist_ok=True)
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            guest_name TEXT,
            guest_type TEXT,
            language TEXT,
            contact TEXT,
            channel TEXT,
            status TEXT,
            error_message TEXT
        )
    """)
    conn.commit()
    conn.close()

init_local_db()

def save_to_local(entry):
    """Save failed log locally for retry."""
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO failed_logs 
        (timestamp, guest_name, guest_type, language, contact, channel, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.get("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        entry.get("Guest Name", ""),
        entry.get("Guest Type", "standard"),
        entry.get("Language", "en"),
        entry.get("Contact", ""),
        entry.get("Channel", ""),
        entry.get("Status", ""),
        entry.get("ErrorMessage", ""),
    ))
    conn.commit()
    conn.close()
    print(f"💾 Saved log locally for retry: {entry.get('Guest Name')} ({entry.get('Channel')})")

# === GOOGLE SHEETS CLIENT INITIALIZATION ===
def init_client():
    """Initialize the Google Sheets client safely."""
    global client
    if client is not None:
        return client
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
        client = gspread.authorize(creds)
        print("✅ Successfully authenticated with Google Sheets.")
    except FileNotFoundError:
        print(f"❌ Credentials file not found at {CREDS_FILE}.")
        client = None
    except Exception as e:
        print(f"❌ Failed to authenticate with Google Sheets: {e}")
        client = None
    return client

# === OPEN SHEET SAFELY ===
def _open_sheet(sheet_id, sheet_name="Unknown"):
    if not sheet_id:
        print(f"⚠️ No spreadsheet ID provided for {sheet_name}. Check your config or .env file.")
        return None
    c = init_client()
    if not c:
        return None
    try:
        return c.open_by_key(sheet_id).sheet1
    except gspread.SpreadsheetNotFound:
        print(f"⚠️ Spreadsheet '{sheet_name}' not found or not shared with service account. ID={sheet_id}")
    except Exception as e:
        print(f"⚠️ Error opening {sheet_name} sheet (ID={sheet_id}): {e}")
    return None

# === GUEST BOOKINGS ===
def get_new_guest_bookings():
    """Fetch all NEW guest bookings (Status != 'Processed')"""
    sheet = _open_sheet(SPREADSHEET_GUEST_ASSIST_ID, "Guest Assist")
    if not sheet:
        return []
    try:
        data = sheet.get_all_records()
        new_bookings = [row for row in data if row.get("Status", "").lower() != "processed"]
        return new_bookings
    except Exception as e:
        print(f"⚠️ Error fetching Guest Assist sheet: {e}")
        return []

def update_booking_status(guest_name, status="Processed"):
    """Update booking status for a specific guest."""
    sheet = _open_sheet(SPREADSHEET_GUEST_ASSIST_ID, "Guest Assist")
    if not sheet:
        return "❌ Sheet not available."

    try:
        data = sheet.get_all_records()
        headers = sheet.row_values(1)
        status_col = headers.index("Status") + 1
        name_col = headers.index("Guest Name")

        for i, row in enumerate(data, start=2):
            if row.get("Guest Name") == guest_name:
                sheet.update_cell(i, status_col, status)
                print(f"✅ Updated booking for {guest_name} → {status}")
                return f"✅ Updated booking for {guest_name} → {status}"
        return f"⚠️ Guest '{guest_name}' not found."
    except Exception as e:
        print(f"⚠️ Error updating booking for {guest_name}: {e}")
        return f"❌ Error updating booking: {e}"

# === HOTEL CONTACTS ===
def get_hotel_contacts():
    """Return all hotel contacts as a list of dicts."""
    sheet = _open_sheet(SPREADSHEET_HOTEL_CONTACTS_ID, "Hotel Contacts")
    if not sheet:
        return []
    try:
        records = sheet.get_all_records()
        return [
            {
                "Hotel name": row.get("Hotel name", "").strip(),
                "email": row.get("Email", "").strip(),
                "phone": row.get("Phone", "").strip()
            }
            for row in records if row.get("Hotel name")
        ]
    except Exception as e:
        print(f"⚠️ Error fetching hotel contacts: {e}")
        return []

# === NOTIFICATION LOG ===
def add_notification_log(entry):
    """
    Add a log entry to NotificationsLog sheet.
    Falls back to SQLite if Sheets quota fails.
    """
    sheet = _open_sheet(SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log")
    if not sheet:
        save_to_local(entry)
        return

    try:
        row = [
            entry.get("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            entry.get("Guest Name", ""),
            entry.get("Guest Type", "standard"),
            entry.get("Language", "en"),
            entry.get("Contact", ""),
            entry.get("Channel", ""),
            entry.get("Status", ""),
            entry.get("ErrorMessage", ""),
        ]
        sheet.append_row(row)
        print(f"📝 Logged {entry.get('Channel')} notification for {entry.get('Guest Name')} ({entry.get('Language')}).")
    except Exception as e:
        print(f"⚠️ Sheets logging failed, saving locally instead. Error: {e}")
        save_to_local(entry)

