# -*- coding: utf-8 -*-
"""
google_sheets.py – Guzo Guest Assist (v11)
----------------------------------------------------
Handles:
- Secure authentication using service account credentials
- Loading & caching Google Sheets
- Hotel contact lookup (ID, Email, Telegram, Phone, Sheet ID)
- Booking logging into each hotel's sheet in the correct format
- Fuzzy matching (“Did you mean…”) suggestions
- Safe payment update handling with duplicate-header protection
"""

import os
import gspread
from datetime import datetime
from difflib import get_close_matches
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Load environment variables
# ----------------------------------------------------------------------
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_CACHE = {}

# ----------------------------------------------------------------------
# Secure Google Sheets Client Initialization
# ----------------------------------------------------------------------
def init_client():
    """Initialize Google Sheets client using service account credentials."""
    try:
        creds_path = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "C:/Users/Gedan/Desktop/Guzo/guzo_booking_bot/creds/guzo_service_account.json",
        )
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credential file not found: {creds_path}")

        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        print("✅ Google Sheets client initialized successfully.")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Google Sheets client: {e}")
        return None


# ----------------------------------------------------------------------
# Cached Sheet Loader
# ----------------------------------------------------------------------
def open_sheet(sheet_id_or_name, client=None):
    """Open a Google Sheet by ID or name (cached)."""
    try:
        if client is None:
            client = init_client()
        if not client:
            return None

        if sheet_id_or_name in SHEET_CACHE:
            return SHEET_CACHE[sheet_id_or_name]

        try:
            sheet = client.open_by_key(sheet_id_or_name).sheet1
        except Exception:
            sheet = client.open(sheet_id_or_name).sheet1

        SHEET_CACHE[sheet_id_or_name] = sheet
        print(f"📄 Opened sheet: {sheet_id_or_name}")
        return sheet
    except Exception as e:
        print(f"⚠️ Error opening sheet: {e}")
        return None


# ----------------------------------------------------------------------
# Master Sheet Access
# ----------------------------------------------------------------------
def get_hotel_contact_sheet_id():
    """Detect Hotel Contacts Master Sheet ID from available .env keys."""
    sheet_id = (
        os.getenv("HOTEL_CONTACT_SHEET_ID")
        or os.getenv("Hotel_Contacts_Master")
        or os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS_MASTER")
    )
    if sheet_id:
        print(f"🔍 Using Hotel Contacts Sheet ID from .env: {sheet_id[:15]}...")
    else:
        print("⚠️ No Hotel Contacts Master Sheet ID found in .env file.")
    return sheet_id


def load_hotel_contacts():
    """Load all hotel contact rows."""
    try:
        sheet_id = get_hotel_contact_sheet_id()
        if not sheet_id:
            return []
        client = init_client()
        if not client:
            return []
        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_records()
        print(f"✅ Loaded {len(records)} hotel contacts.")
        return records
    except Exception as e:
        print(f"⚠️ Error loading hotel contacts: {e}")
        return []


# ----------------------------------------------------------------------
# Hotel Lookup (Fuzzy Match + Contact Access)
# ----------------------------------------------------------------------
def find_hotel_record(hotel_query):
    """
    Fuzzy match hotel info from the Hotel Contacts Master sheet.
    - Matches even if guest types partial or natural phrases.
    - Suggests close matches if no exact match.
    """
    try:
        records = load_hotel_contacts()
        if not records:
            return None

        query = hotel_query.lower().replace("-", "").replace("hotel", "").strip()
        normalized_map = {
            str(row.get("Hotel Name", "")).lower().replace("-", "").replace("hotel", "").strip(): row
            for row in records if row.get("Hotel Name")
        }

        # exact or partial match
        for key, row in normalized_map.items():
            if key in query or query in key:
                print(f"🏨 Matched hotel record for: {row.get('Hotel Name')}")
                return row

        # fuzzy suggestion
        close_matches = get_close_matches(query, list(normalized_map.keys()), n=1, cutoff=0.6)
        if close_matches:
            suggestion = normalized_map[close_matches[0]].get("Hotel Name", "")
            print(f"💡 Did you mean: {suggestion}?")
            return {"suggested_name": suggestion}

        print(f"⚠️ No hotel matched fuzzy query: '{hotel_query}'")
        return None
    except Exception as e:
        print(f"⚠️ Error in find_hotel_record: {e}")
        return None


def get_hotel_contact_phone(hotel_name: str) -> str:
    """Return the phone number for a hotel."""
    record = find_hotel_record(hotel_name)
    if record and "Phone" in record:
        phone = str(record.get("Phone", "N/A")).strip()
        if phone:
            print(f"📞 Found phone for {hotel_name}: {phone}")
            return phone
    print(f"⚠️ No phone record found for {hotel_name}")
    return "N/A"


def get_manager_chat_id(hotel_name: str):
    """Retrieve the Telegram Chat ID of a hotel's manager."""
    try:
        record = find_hotel_record(hotel_name)
        if record and "Telegram Chat ID" in record:
            chat_id_str = str(record["Telegram Chat ID"]).strip()
            if chat_id_str.replace("-", "").isdigit():
                print(f"📱 Found Telegram Chat ID for {hotel_name}: {chat_id_str}")
                return int(chat_id_str)
        print(f"⚠️ No Telegram Chat ID available for {hotel_name}")
        return None
    except Exception as e:
        print(f"⚠️ Error retrieving manager chat ID: {e}")
        return None


# ----------------------------------------------------------------------
# Logging Utilities
# ----------------------------------------------------------------------
def log_new_request(guest_name, hotel_name, message, status="Pending"):
    """
    Append a booking/cancellation request to the master log sheet.
    """
    try:
        master_id = get_hotel_contact_sheet_id()
        if not master_id:
            print("⚠️ Master sheet not configured. Logging locally instead.")
            os.makedirs("logs", exist_ok=True)
            with open("logs/local_request_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} | {guest_name} | {hotel_name} | {message} | {status}\n")
            return False

        client = init_client()
        if not client:
            return False

        sheet = client.open_by_key(master_id).sheet1
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), guest_name, hotel_name, message, status]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"🗂️ Logged new request for {guest_name} ({hotel_name}) → {status}")
        return True
    except Exception as e:
        print(f"⚠️ Could not log new request: {e}")
        return False


def log_booking(hotel, guests, dates, room, guest_name, timestamp):
    """Append booking info to a hotel's booking sheet."""
    try:
        record = find_hotel_record(hotel)
        if not record:
            raise ValueError(f"No hotel record found for {hotel}")
        if "suggested_name" in record:
            raise ValueError(f"Hotel name unclear — did you mean {record['suggested_name']}?")

        sheet_id = record.get("Sheet ID")
        if not sheet_id:
            raise ValueError(f"No Sheet ID for {hotel}")

        client = init_client()
        if not client:
            raise ValueError("Google Sheets client unavailable")

        sheet = client.open_by_key(sheet_id).sheet1
        new_row = [
            timestamp,
            guest_name,
            "Telegram",
            dates,
            "",
            room,
            "",
            "",
            "Pending",
            "Guzo Guest Assist",
            "Auto-booked via bot",
            "Sent",
            "Guzo System",
        ]
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        print(f"✅ Logged booking for {hotel} ({guest_name}) to {sheet.title}")
        return True
    except Exception as e:
        print(f"⚠️ Error while logging booking: {e}")
        return False


# ----------------------------------------------------------------------
# Payment Updater with Header Validation
# ----------------------------------------------------------------------
def update_payment_status(confirmation_id: str, amount: str, currency: str = "ETB"):
    """Update booking status to 'Paid' safely."""
    try:
        client = init_client()
        if not client:
            print("⚠️ Google Sheets client unavailable.")
            return False

        master_id = get_hotel_contact_sheet_id()
        if not master_id:
            print("⚠️ Hotel master sheet not found.")
            return False

        master_sheet = client.open_by_key(master_id).sheet1
        hotels = master_sheet.get_all_records()

        for hotel in hotels:
            sheet_id = hotel.get("Sheet ID")
            hotel_name = hotel.get("Hotel Name")
            if not sheet_id:
                continue
            try:
                sheet = client.open_by_key(sheet_id).sheet1
                data = sheet.get_all_values()
                if not data or not data[0]:
                    print(f"⚠️ Skipping {hotel_name}: empty header.")
                    continue

                headers = [h.strip().lower() for h in data[0] if h.strip()]
                if len(headers) != len(set(headers)):
                    print(f"⚠️ Skipping {hotel_name}: duplicate headers.")
                    continue
                if "confirmation id" not in headers:
                    continue

                col_idx = headers.index("confirmation id")
                status_idx = headers.index("booking status") if "booking status" in headers else None
                pay_idx = headers.index("payment status") if "payment status" in headers else None
                date_idx = headers.index("payment date") if "payment date" in headers else None
                revenue_idx = headers.index("revenue (etb)") if "revenue (etb)" in headers else None

                for i, row in enumerate(data[1:], start=2):
                    if str(row[col_idx]).strip() == confirmation_id.strip():
                        print(f"💰 Match found in {hotel_name} for {confirmation_id}")
                        if status_idx is not None:
                            sheet.update_cell(i, status_idx + 1, "Paid ✅")
                        if pay_idx is not None:
                            sheet.update_cell(i, pay_idx + 1, f"Paid {amount} {currency}")
                        if date_idx is not None:
                            sheet.update_cell(i, date_idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        if revenue_idx is not None:
                            sheet.update_cell(i, revenue_idx + 1, amount)
                        print(f"✅ Payment status updated for {confirmation_id} ({amount} {currency})")
                        return True
            except Exception as e:
                print(f"⚠️ Could not update {hotel_name}: {e}")
                continue
        print(f"⚠️ No booking found with Confirmation ID: {confirmation_id}")
        return False
    except Exception as e:
        print(f"❌ Error updating payment status: {e}")
        return False


# ----------------------------------------------------------------------
# Test Runner
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("🔍 Testing Google Sheets connection...")
    client = init_client()
    if client:
        for test_hotel in ["Sofi Hotel", "Sky Light Hotel"]:
            print(f"\nAttempting sample booking for {test_hotel}...")
            log_booking(
                hotel=test_hotel,
                guests="2",
                dates="Oct 25–27",
                room="Deluxe",
                guest_name="Tester",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
