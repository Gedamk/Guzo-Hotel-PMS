# -*- coding: utf-8 -*-
"""
log_helper.py – Hybrid logging utility for Guzo Guest Assist
------------------------------------------------------------
• Logs events locally to backend/logs/system_events.log
• Optionally sends the same log to Google Sheets ("Guzo_Notification_Log")
• Safe fallback — will never crash if Sheets is unreachable.
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# === Load Environment Variables ===
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env", override=True)

# === Optional Google Sheets Integration ===
try:
    import gspread
except ImportError:
    gspread = None

# === Local Logging Setup ===
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_events.log")

# === Environment Path for Credentials ===
CREDENTIALS_PATH = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json"
)

# === Google Sheet Configuration ===
NOTIFICATION_SHEET_NAME = "Guzo_Notification_Log"
NOTIFICATION_TAB = "Bookings"


def log_event(module: str, status: str, message: str):
    """Log events locally and (if possible) to Google Sheets."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {module} | {status} | {message}\n"

    # --- Local Logging ---
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

    # --- Google Sheets Logging (safe optional) ---
    if gspread and os.path.exists(CREDENTIALS_PATH):
        try:
            sa = gspread.service_account(filename=CREDENTIALS_PATH)
            sheet = sa.open(NOTIFICATION_SHEET_NAME).worksheet(NOTIFICATION_TAB)
            result = sheet.append_row(
                [timestamp, module, status, message],
                value_input_option="USER_ENTERED"
            )

            # ✅ Treat any <Response [200]> or None as success
            if hasattr(result, "status_code"):
                code = getattr(result, "status_code", None)
                if code == 200:
                    print(f"📤 Logged to Google Sheets successfully ({NOTIFICATION_SHEET_NAME} → {NOTIFICATION_TAB})")
                else:
                    print(f"⚠️  Unexpected Sheets response code: {code}")
            else:
                print(f"📤 Logged to Google Sheets successfully ({NOTIFICATION_SHEET_NAME} → {NOTIFICATION_TAB})")

        except Exception as e:
            err = str(e)
            if "<Response [200]>" in err:
                print(f"📤 Logged to Google Sheets successfully ({NOTIFICATION_SHEET_NAME} → {NOTIFICATION_TAB})")
            else:
                print(f"⚠️  Could not log to Google Sheets: {e}")
    else:
        print("ℹ️  Google Sheets logging skipped (module or credentials missing).")
