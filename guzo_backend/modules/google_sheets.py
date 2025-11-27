# -*- coding: utf-8 -*-
"""
google_sheets.py – Guzo Guest Assist Google Sheets Manager (v27.0)
-------------------------------------------------------------------
Role in the CURRENT architecture:

    • PostgreSQL is the PRIMARY source of truth (hotels, bookings, reports).
    • Google Sheets is OPTIONAL and should NEVER break dashboards.
    • When credentials are missing, we:
        - Return safe fallbacks (e.g. static hotel list)
        - Log a single, calm warning
        - Do NOT raise hard exceptions

✅ Dual Google Sheets Support (when enabled):
   1️⃣ Hotel_Contact_Master → HOTEL_CONTACT_SHEET_ID
   2️⃣ Guzo_Central_System  → CENTRAL_DASHBOARD_SHEET_ID / Central_Bookings

✅ Features:
   - Safe client initialization with graceful failure
   - Header sanitizer + schema checker
   - UTF-8 friendly, GDPR-aware logging
   - Backward-compatible helpers for older modules

This version is aligned with:
   • React portfolio dashboard using FastAPI + PostgreSQL
   • Streamlit hotel dashboards using PostgreSQL as primary source
   • Sheets used only as an optional integration layer
"""

import os
import datetime
from typing import List, Optional, Dict, Any

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

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

# Internal cache / flags (to avoid spamming logs)
_client_cached = None
_client_error_logged = False
_missing_creds_warned = False

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
# 🔑 Initialize Google Sheets Client (SAFE)
# ============================================================
def init_client():
    """
    Initialize Google Sheets client.

    Best practice (current phase):
        • If credentials file is missing or invalid, return None.
        • Log a warning ONCE, do NOT crash the app.
    """
    global _client_cached, _client_error_logged, _missing_creds_warned

    if _client_cached is not None:
        return _client_cached

    # Check existence of service account file
    if not SERVICE_ACCOUNT_FILE or not os.path.exists(SERVICE_ACCOUNT_FILE):
        if not _missing_creds_warned:
            print(
                f"[GuzoSheets] ⚠️ service_account.json not found at "
                f"'{SERVICE_ACCOUNT_FILE}'. Sheets integration is DISABLED "
                "in this environment. (Using database + static fallbacks.)"
            )
            _missing_creds_warned = True
        _client_cached = None
        return None

    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        _client_cached = client
        print("[GuzoSheets] ✅ Google Sheets client initialized successfully.")
        return client
    except Exception as e:
        if not _client_error_logged:
            print(f"[GuzoSheets] ❌ Client initialization failed: {e}")
            _client_error_logged = True
        _client_cached = None
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
# 📄 Generic Reader (header-safe + FAIL-SOFT)
# ============================================================
def get_sheet_as_df(
    sheet_id: str, tab_name: str, expected_headers: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Read a tab as a DataFrame, optionally enforcing expected headers.

    CURRENT BEHAVIOR:
        • If Sheets client not available → return empty DataFrame.
        • Never raises a hard error; always safe for dashboards.
    """
    client = init_client()
    if client is None:
        print(
            f"[GuzoSheets] ℹ️ Sheets client not available – returning empty "
            f"DataFrame for '{tab_name}'."
        )
        return pd.DataFrame()

    try:
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
            f"[GuzoSheets] ✅ Loaded {len(df)} rows from '{tab_name}' "
            f"(ID: {sheet_id[:8]}...)"
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

    If Sheets are disabled, returns False without raising errors.
    """
    client = init_client()
    if client is None or not CENTRAL_DASHBOARD_SHEET_ID:
        print(
            "[SchemaCheck] ℹ️ Sheets disabled or CENTRAL_DASHBOARD_SHEET_ID "
            "missing – skipping schema check."
        )
        return False

    try:
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
            "[SchemaCheck] ⚠️ Schema mismatch detected. "
            "Please review header alignment."
        )
        return False
    except Exception as e:
        print(f"[SchemaCheck] ❌ Failed to verify schema: {e}")
        return False


# ============================================================
# 🏨 Read Hotel Contact Master (with STATIC FALLBACK)
# ============================================================
def _static_hotels_fallback() -> pd.DataFrame:
    """
    Static fallback list used when Sheets are disabled.

    Aligns with the current test hotels in PostgreSQL:
        - DRE001  Dream Big Hotel
        - N&N002  N&N Luxury Hotel
    """
    hotels = [
        {
            "Hotel Name": "Dream Big Hotel",
            "Property Code": "DRE001",
            "Location": "Addis Ababa",
            "Sheet ID": "",
            "Main Contact Email": "",
            "Reservation Email": "",
            "Phone": "",
            "Telegram Chat ID": "",
            "Manager Name": "",
            "Preferred Language": "EN",
            "Currency": "ETB",
            "Integration Status": "LOCAL_ONLY",
        },
        {
            "Hotel Name": "N&N Luxury Hotel",
            "Property Code": "N&N002",
            "Location": "Addis Ababa",
            "Sheet ID": "",
            "Main Contact Email": "",
            "Reservation Email": "",
            "Phone": "",
            "Telegram Chat ID": "",
            "Manager Name": "",
            "Preferred Language": "EN",
            "Currency": "ETB",
            "Integration Status": "LOCAL_ONLY",
        },
    ]
    df = pd.DataFrame(hotels)
    print(
        f"[GuzoSheets] ℹ️ read_hotels_master() using STATIC fallback list "
        f"({len(df)} hotels)."
    )
    return df


def read_hotels_master() -> pd.DataFrame:
    """
    Return all hotel properties (header-safe).

    ORDER OF PRIORITY:
        1. If Sheets client + HOTEL_CONTACT_SHEET_ID available → read live sheet.
        2. Otherwise → use _static_hotels_fallback() so dashboards still work.
    """
    if not HOTEL_CONTACT_SHEET_ID or init_client() is None:
        # No Sheets available: use static fallback.
        return _static_hotels_fallback()

    try:
        df = get_sheet_as_df(
            HOTEL_CONTACT_SHEET_ID,
            HOTEL_CONTACT_TAB_NAME,
            expected_headers=HOTEL_HEADERS,
        )
        if df.empty:
            print(
                f"[GuzoSheets] ⚠️ No data found in '{HOTEL_CONTACT_TAB_NAME}'. "
                "Using static fallback list."
            )
            return _static_hotels_fallback()

        print(
            f"[GuzoSheets] ✅ Loaded {len(df)} hotels from "
            f"'{HOTEL_CONTACT_TAB_NAME}'."
        )
        return df
    except Exception as e:
        print(f"[GuzoSheets] ❌ read_hotels_master() failed: {e}")
        return _static_hotels_fallback()


# ============================================================
# 🧾 Read Central Dashboard Bookings (optional)
# ============================================================
def read_central_bookings() -> pd.DataFrame:
    """
    Read bookings from Central_Bookings tab.

    If Sheets are disabled, returns an empty DataFrame.
    """
    if not CENTRAL_DASHBOARD_SHEET_ID or init_client() is None:
        print(
            "[GuzoSheets] ℹ️ read_central_bookings() – Sheets disabled or "
            "CENTRAL_DASHBOARD_SHEET_ID missing; returning empty DataFrame."
        )
        return pd.DataFrame()

    try:
        df = get_sheet_as_df(
            CENTRAL_DASHBOARD_SHEET_ID,
            CENTRAL_DASHBOARD_SHEET_NAME,
            expected_headers=BOOKING_COLUMNS,
        )
        if df.empty:
            print(
                f"[GuzoSheets] ⚠️ No data found in "
                f"'{CENTRAL_DASHBOARD_SHEET_NAME}'."
            )
        else:
            print(
                f"[GuzoSheets] ✅ Loaded {len(df)} bookings from "
                f"'{CENTRAL_DASHBOARD_SHEET_NAME}'."
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
            f"[SchemaError] Expected {len(PROPERTY_BOOKING_COLUMNS)} columns for "
            f"property sheet, got {len(row)}."
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
            f"[SchemaError] Expected {len(BOOKING_COLUMNS)} columns for central "
            f"sheet, got {len(row)}."
        )
    return row


# ============================================================
# ✍️ Append Booking – HOTEL SHEET ONLY (optional)
# ============================================================
def append_booking(data: dict) -> bool:
    """
    Append booking to the hotel's Booking sheet ONLY.

    Per-property Booking sheet columns:
    Timestamp, Guest Name, Source, Check-In Date, Check-Out Date, Nights,
    Room Type, Rate Per Night (ETB), Total Revenue (ETB), Booking Status,
    Confirmation ID, Payment Status, Payment Date, Payment Method,
    Handled By, Auto Reply, Remark

    If Sheets are disabled or Sheet ID missing, returns False without raising.
    """
    hotel_name = data.get("Hotel Name", "Unknown Hotel")
    sheet_id = data.get("Sheet ID")

    if not sheet_id:
        print(
            f"[GuzoSheets] ⚠️ Missing hotel Sheet ID for {hotel_name}; "
            "skipping hotel sheet append."
        )
        return False

    client = init_client()
    if client is None:
        print(
            f"[GuzoSheets] ℹ️ Sheets disabled – cannot append booking to "
            f"hotel sheet for {hotel_name}."
        )
        return False

    try:
        row = _build_property_booking_row(data)
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
# 🧾 Central-only logger (optional)
# ============================================================
def log_booking_to_central(data: dict) -> bool:
    """
    Append booking only to Central_Bookings (no hotel sheet required).

    If Sheets are disabled or ID missing, returns False without raising.
    """
    if not CENTRAL_DASHBOARD_SHEET_ID:
        print(
            "[GuzoSheets] ⚠️ CENTRAL_DASHBOARD_SHEET_ID not set; "
            "cannot write to central."
        )
        return False

    client = init_client()
    if client is None:
        print(
            "[GuzoSheets] ℹ️ Sheets disabled – cannot append booking to "
            "Central_Bookings."
        )
        return False

    try:
        row = _build_booking_row(data)
        ws2 = client.open_by_key(CENTRAL_DASHBOARD_SHEET_ID).worksheet(
            CENTRAL_DASHBOARD_SHEET_NAME
        )
        ws2.append_row(row, value_input_option="USER_ENTERED")
        print(
            f"[GuzoSheets] ✅ Booking logged to Central Dashboard "
            f"({CENTRAL_DASHBOARD_SHEET_NAME})"
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
        f"[GuzoSheets] ⚙️ Using legacy _open_sheet() redirect → "
        f"get_sheet_as_df('{tab_name}')"
    )
    return get_sheet_as_df(sheet_id, tab_name)


SPREADSHEET_NOTIFICATIONSLOG_ID = CENTRAL_DASHBOARD_SHEET_ID


def get_hotel_contacts():
    print(
        "[GuzoSheets] ⚙️ Redirecting legacy get_hotel_contacts() → "
        "read_hotels_master()"
    )
    return read_hotels_master()


def load_hotel_contacts():
    print(
        "[GuzoSheets] ⚙️ Redirecting legacy load_hotel_contacts() → "
        "read_hotels_master()"
    )
    return read_hotels_master()


def sync_to_master(row: dict) -> bool:
    """
    Legacy shim to keep old callers working.

    NEW BEHAVIOR (aligned with v27.0):
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
    print("✅ Test completed (no crashes).")
