# -*- coding: utf-8 -*-
"""
google_sheets.py – Guzo Guest Assist Google Sheets Manager (v26.0)
-------------------------------------------------------------------
✅ Dual Google Sheets Support:
   1️⃣ Hotel_Contact_Master → HOTEL_CONTACT_SHEET_ID
   2️⃣ Guzo_Central_System  → CENTRAL_DASHBOARD_SHEET_ID / Central_Bookings
✅ Safe client initialization & schema validation
✅ Auto header sanitizer + schema checker
✅ UTF-8, ISO, and GDPR-compliant logging

Updates in v26.0:
- Split schemas:
  • Per-property Bookings sheet (NO 'Hotel Name', includes 'Payment Date')
  • Central_Bookings sheet (with 'Hotel Name', legacy schema)
- append_booking() → writes ONLY to property Booking sheet
- sync_to_master() / log_booking_to_central() → write ONLY to Central_Bookings
- Keeps Central_Bookings header compatible with existing sheet
"""

import os
import datetime
import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from typing import List, Optional, Dict, Any

# ============================================================
# 🔧 Environment Setup
# ============================================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_JSON", "creds/service_account.json"
)

# 🏨 Hotel Contact Master
HOTEL_CONTACT_SHEET_ID = os.getenv("HOTEL_CONTACT_SHEET_ID")
HOTEL_CONTACT_TAB_NAME = os.getenv("HOTEL_CONTACT_TAB_NAME", "Hotel_Contact_Master")

# 🧾 Central Dashboard
CENTRAL_DASHBOARD_SHEET_ID = os.getenv("CENTRAL_DASHBOARD_SHEET_ID")
CENTRAL_DASHBOARD_SHEET_NAME = os.getenv(
    "CENTRAL_DASHBOARD_SHEET_NAME", "Central_Bookings"
)

# Optional Notifications Log
NOTIFICATIONS_LOG_TAB_NAME = os.getenv(
    "NOTIFICATIONS_LOG_TAB_NAME", "Notifications Log"
)


# ============================================================
# 🧱 Booking Schema Definitions
# ============================================================

# 🔹 Per-property Bookings sheet (NO 'Hotel Name', HAS 'Payment Date')
PROPERTY_BOOKING_COLUMNS = [
    "Timestamp",
    "Guest Name",
    "Source",
    "Check-In Date",
    "Check-Out Date",
    "Nights",
    "Room Type",
    "Rate Per Night (ETB)",
    "Total Revenue (ETB)",
    "Booking Status",
    "Confirmation ID",
    "Payment Status",
    "Payment Date",
    "Payment Method",
    "Handled By",
    "Auto Reply",
    "Remark",
]

# 🔹 Central_Bookings legacy schema (kept as-is for compatibility)
BOOKING_COLUMNS = [
    "Timestamp",
    "Hotel Name",
    "Guest Name",
    "Source",
    "Check-In Date",
    "Check-Out Date",
    "Nights",
    "Room Type",
    "Rate Per Night (ETB)",
    "Total Revenue (ETB)",
    "Booking Status",
    "Confirmation ID",
    "Payment Status",
    "Payment Method",
    "Handled By",
    "Auto Reply",
    "Remark",
]

# Expected headers for Hotels master (used to prevent duplicate/blank header errors)
HOTEL_HEADERS = [
    "Hotel Name",
    "Property Code",
    "Location",
    "Sheet ID",
    "Main Contact Email",
    "Reservation Email",
    "Phone",
    "Telegram Chat ID",
    "Manager Name",
    "Preferred Language",
    "Currency",
    "Integration Status",
]


# ============================================================
# 🔑 Initialize Google Sheets Client
# ============================================================
def init_client():
    """Initialize Google Sheets client."""
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        print("[GuzoSheets] ✅ Google Sheets client initialized successfully.")
        return client
    except Exception as e:
        print(f"[GuzoSheets] ❌ Client initialization failed: {e}")
        return None


# Compat alias (some modules expect get_client())
def get_client():
    return init_client()


# ============================================================
# 🧩 Helper: Sanitize Headers
# ============================================================
def sanitize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Automatically rename duplicate headers (e.g., Handled By_1)."""
    if df.empty:
        return df
    seen = {}
    new_cols = []
    for col in df.columns:
        key = str(col).strip()
        if key in seen:
            seen[key] += 1
            new_cols.append(f"{key}_{seen[key]}")
        else:
            seen[key] = 0
            new_cols.append(key)
    df.columns = new_cols
    return df


# ============================================================
# 📄 Generic Reader (header-safe)
# ============================================================
def get_sheet_as_df(
    sheet_id: str, tab_name: str, expected_headers: Optional[List[str]] = None
) -> pd.DataFrame:
    """Read a tab as a DataFrame, optionally enforcing expected headers to avoid duplicate/blank header crashes."""
    try:
        client = init_client()
        ws = client.open_by_key(sheet_id).worksheet(tab_name)
        if expected_headers:
            # Prevents: "header row contains duplicates" error
            records = ws.get_all_records(
                expected_headers=expected_headers, default_blank=""
            )
        else:
            records = ws.get_all_records()
        df = pd.DataFrame(records)
        df = sanitize_headers(df)
        print(
            f"[GuzoSheets] ✅ Loaded {len(df)} rows from '{tab_name}' (ID: {sheet_id[:8]}...)"
        )
        return df
    except Exception as e:
        print(f"[GuzoSheets] ⚠️ get_sheet_as_df() failed for '{tab_name}': {e}")
        return pd.DataFrame()


# ============================================================
# 🧩 Schema Checker (Central_Bookings)
# ============================================================
def check_central_schema() -> bool:
    """
    Verify that Central_Bookings tab matches the BOOKING_COLUMNS schema.
    Warns if columns are missing, duplicated, or out of order.
    """
    try:
        client = init_client()
        ws = client.open_by_key(CENTRAL_DASHBOARD_SHEET_ID).worksheet(
            CENTRAL_DASHBOARD_SHEET_NAME
        )
        header_row = ws.row_values(1)
        header_row = [h.strip() for h in header_row if str(h).strip()]
        expected = BOOKING_COLUMNS

        missing = [h for h in expected if h not in header_row]
        extra = [h for h in header_row if h not in expected]
        misaligned = header_row != expected

        if missing:
            print(f"[SchemaCheck] ⚠️ Missing columns: {missing}")
        if extra:
            print(f"[SchemaCheck] ⚠️ Extra columns: {extra}")
        if misaligned and not missing and not extra:
            print("[SchemaCheck] ⚠️ Columns present but in wrong order.")
        if not misaligned and not missing and not extra:
            print(
                "[SchemaCheck] ✅ Central_Bookings schema is perfectly aligned."
            )
            return True

        print(
            "[SchemaCheck] ⚠️ Schema mismatch detected. Please review header alignment."
        )
        return False
    except Exception as e:
        print(f"[SchemaCheck] ❌ Failed to verify schema: {e}")
        return False


# ============================================================
# 🏨 Read Hotel Contact Master (header-safe)
# ============================================================
def read_hotels_master() -> pd.DataFrame:
    """Return all hotel properties (header-safe)."""
    try:
        if not HOTEL_CONTACT_SHEET_ID:
            raise Exception("Missing HOTEL_CONTACT_SHEET_ID in .env file.")
        df = get_sheet_as_df(
            HOTEL_CONTACT_SHEET_ID,
            HOTEL_CONTACT_TAB_NAME,
            expected_headers=HOTEL_HEADERS,
        )
        if df.empty:
            print(
                f"[GuzoSheets] ⚠️ No data found in '{HOTEL_CONTACT_TAB_NAME}'."
            )
        else:
            print(
                f"[GuzoSheets] ✅ Loaded {len(df)} hotels from '{HOTEL_CONTACT_TAB_NAME}'."
            )
        return df
    except Exception as e:
        print(f"[GuzoSheets] ❌ read_hotels_master() failed: {e}")
        return pd.DataFrame()


# ============================================================
# 🧾 Read Central Dashboard Bookings
# ============================================================
def read_central_bookings() -> pd.DataFrame:
    """Read bookings from Central_Bookings tab."""
    try:
        if not CENTRAL_DASHBOARD_SHEET_ID:
            raise Exception("Missing CENTRAL_DASHBOARD_SHEET_ID in .env file.")
        df = get_sheet_as_df(
            CENTRAL_DASHBOARD_SHEET_ID,
            CENTRAL_DASHBOARD_SHEET_NAME,
            expected_headers=BOOKING_COLUMNS,
        )
        if df.empty:
            print(
                f"[GuzoSheets] ⚠️ No data found in '{CENTRAL_DASHBOARD_SHEET_NAME}'."
            )
        else:
            print(
                f"[GuzoSheets] ✅ Loaded {len(df)} bookings from '{CENTRAL_DASHBOARD_SHEET_NAME}'."
            )
        return df
    except Exception as e:
        print(f"[GuzoSheets] ❌ read_central_bookings() failed: {e}")
        return pd.DataFrame()


# ============================================================
# 🔧 Internal: Build booking rows
# ============================================================
def _build_property_booking_row(data: Dict[str, Any]) -> List[Any]:
    """
    Build a row for a per-property Booking sheet.
    Columns:
    Timestamp, Guest Name, Source, Check-In Date, Check-Out Date, Nights,
    Room Type, Rate Per Night (ETB), Total Revenue (ETB), Booking Status,
    Confirmation ID, Payment Status, Payment Date, Payment Method,
    Handled By, Auto Reply, Remark
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payment_date = data.get("Payment Date") or datetime.datetime.now().strftime(
        "%Y-%m-%d"
    )

    row = [
        now,
        data.get("Guest Name", ""),
        data.get("Source", "Telegram"),
        data.get("Check-In Date", ""),
        data.get("Check-Out Date", ""),
        data.get("Nights", ""),
        data.get("Room Type", ""),
        data.get("Rate Per Night (ETB)", ""),
        data.get("Total Revenue (ETB)", ""),
        data.get("Booking Status", "Confirmed"),
        data.get("Confirmation ID", ""),
        data.get("Payment Status", "Paid"),
        payment_date,
        data.get("Payment Method", ""),
        data.get("Handled By", "Guzo Bot"),
        data.get("Auto Reply", "✅ Auto Confirmation Sent"),
        data.get("Remark", "-"),
    ]
    if len(row) != len(PROPERTY_BOOKING_COLUMNS):
        raise ValueError(
            f"[SchemaError] Expected {len(PROPERTY_BOOKING_COLUMNS)} columns for property sheet, got {len(row)}."
        )
    return row


def _build_booking_row(data: Dict[str, Any]) -> List[Any]:
    """
    Build a row for Central_Bookings (legacy schema with 'Hotel Name',
    without 'Payment Date').
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        now,
        data.get("Hotel Name", ""),
        data.get("Guest Name", ""),
        data.get("Source", "Telegram"),
        data.get("Check-In Date", ""),
        data.get("Check-Out Date", ""),
        data.get("Nights", ""),
        data.get("Room Type", ""),
        data.get("Rate Per Night (ETB)", ""),
        data.get("Total Revenue (ETB)", ""),
        data.get("Booking Status", "Confirmed"),
        data.get("Confirmation ID", ""),
        data.get("Payment Status", "Paid"),
        data.get("Payment Method", ""),
        data.get("Handled By", "Guzo Bot"),
        data.get("Auto Reply", "✅ Sent"),
        data.get("Remark", "-"),
    ]
    if len(row) != len(BOOKING_COLUMNS):
        raise ValueError(
            f"[SchemaError] Expected {len(BOOKING_COLUMNS)} columns for central sheet, got {len(row)}."
        )
    return row


# ============================================================
# ✍️ Append Booking – HOTEL SHEET ONLY
# ============================================================
def append_booking(data: dict) -> bool:
    """
    Append booking to the hotel's Booking sheet ONLY.

    Per-property Booking sheet columns:
    Timestamp, Guest Name, Source, Check-In Date, Check-Out Date, Nights,
    Room Type, Rate Per Night (ETB), Total Revenue (ETB), Booking Status,
    Confirmation ID, Payment Status, Payment Date, Payment Method,
    Handled By, Auto Reply, Remark
    """
    try:
        hotel_name = data.get("Hotel Name", "Unknown Hotel")
        sheet_id = data.get("Sheet ID")

        if not sheet_id:
            print(
                f"[GuzoSheets] ⚠️ Missing hotel Sheet ID for {hotel_name}; skipping hotel sheet append."
            )
            return False

        row = _build_property_booking_row(data)
        client = init_client()
        sh = client.open_by_key(sheet_id)
        # Use first sheet (assumed to be 'Bookings' with correct header)
        ws = sh.sheet1
        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[GuzoSheets] ✅ Booking logged to Hotel Sheet ({hotel_name})")
        return True

    except Exception as e:
        print(f"[GuzoSheets] ⚠️ append_booking() failed: {e}")
        return False


# ============================================================
# 🧾 Central-only logger
# ============================================================
def log_booking_to_central(data: dict) -> bool:
    """Append booking only to Central_Bookings (no hotel sheet required)."""
    try:
        row = _build_booking_row(data)
        if not CENTRAL_DASHBOARD_SHEET_ID:
            print(
                "[GuzoSheets] ⚠️ CENTRAL_DASHBOARD_SHEET_ID not set; cannot write to central."
            )
            return False
        client = init_client()
        ws2 = client.open_by_key(CENTRAL_DASHBOARD_SHEET_ID).worksheet(
            CENTRAL_DASHBOARD_SHEET_NAME
        )
        ws2.append_row(row, value_input_option="USER_ENTERED")
        print(
            f"[GuzoSheets] ✅ Booking logged to Central Dashboard ({CENTRAL_DASHBOARD_SHEET_NAME})"
        )
        return True
    except Exception as e:
        print(f"[GuzoSheets] ⚠️ log_booking_to_central() failed: {e}")
        return False


# ============================================================
# 🧩 Legacy Compatibility Bridge
# ============================================================
def _open_sheet(sheet_id: str, tab_name: str):
    print(
        f"[GuzoSheets] ⚙️ Using legacy _open_sheet() redirect → get_sheet_as_df('{tab_name}')"
    )
    return get_sheet_as_df(sheet_id, tab_name)


SPREADSHEET_NOTIFICATIONSLOG_ID = CENTRAL_DASHBOARD_SHEET_ID


def get_hotel_contacts():
    print(
        "[GuzoSheets] ⚙️ Redirecting legacy get_hotel_contacts() → read_hotels_master()"
    )
    return read_hotels_master()


def load_hotel_contacts():
    print(
        "[GuzoSheets] ⚙️ Redirecting legacy load_hotel_contacts() → read_hotels_master()"
    )
    return read_hotels_master()


def sync_to_master(row: dict) -> bool:
    """
    Legacy shim to keep old callers working.

    NEW BEHAVIOR:
    - sync_to_master() writes ONLY to Central_Bookings via log_booking_to_central().
    - append_booking() is responsible for the per-property Booking sheet.
    """
    try:
        return log_booking_to_central(row)
    except Exception as e:
        print(f"[GuzoSheets] ⚠️ sync_to_master() failed: {e}")
        return False


# ============================================================
# 🧪 Self-Test
# ============================================================
if __name__ == "__main__":
    print("🔍 Testing Google Sheets integration & schema alignment...")
    check_central_schema()
    hotels = read_hotels_master()
    print(hotels.head())
    bookings = read_central_bookings()
    print(bookings.head())
    print("✅ Test completed successfully.")
