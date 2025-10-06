# -*- coding: utf-8 -*-
"""
Retry Handler
Retries failed notifications with exponential backoff.
Logs results into both Google Sheets and local SQLite backup.
"""

import time
import sqlite3
import sys
from datetime import datetime
from guzo_booking_bot.modules import google_sheets, email_sender, sms_sender, whatsapp_sender

# Retry Settings
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # exponential backoff multiplier
LOCAL_DB = "storage/logs.db"

# ==============================
# Safe Print Wrapper
# ==============================
def safe_print(msg):
    try:
        sys.__stdout__.write(msg + "\n")
    except Exception:
        pass

# ==============================
# SQLite Setup
# ==============================
def init_local_db():
    """Ensure local SQLite database exists."""
    conn = sqlite3.connect(LOCAL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            guest_name TEXT,
            contact TEXT,
            channel TEXT,
            status TEXT,
            error_message TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_local_log(entry):
    """Save retry attempt into SQLite backup."""
    try:
        conn = sqlite3.connect(LOCAL_DB)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO retry_logs (timestamp, guest_name, contact, channel, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.get("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            entry.get("Guest Name", ""),
            entry.get("Contact", ""),
            entry.get("Channel", ""),
            entry.get("Status", ""),
            entry.get("ErrorMessage", "")
        ))
        conn.commit()
        conn.close()
        safe_print(f"📝 Local backup stored for {entry.get('Guest Name')} ({entry.get('Channel')})")
    except Exception as e:
        safe_print(f"❌ Failed to save local log: {e}")

# ==============================
# Retry Logic
# ==============================
def retry_failed_notifications():
    """Retry failed notifications with exponential backoff and dual logging."""
    safe_print("🔄 Starting retry process for failed notifications...")
    init_local_db()

    try:
        logs = google_sheets.get_guest_assist()
    except Exception as e:
        safe_print(f"⚠️ Could not fetch Guest Assist logs: {e}")
        logs = []

    failed_logs = [log for log in logs if str(log.get("Status", "")).lower() == "failed"]

    if not failed_logs:
        safe_print("✅ No failed notifications to retry.")
        return

    for log in failed_logs:
        contact = log.get("Contact", "")
        channel = log.get("Channel", "")
        guest_name = log.get("Guest Name", "Guest")

        safe_print(f"Retrying {channel} for {guest_name} ({contact})...")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if channel.lower() == "email":
                    email_sender.send_email(contact, "Retry Notification", "This is a retry attempt.")
                elif channel.lower() == "sms":
                    sms_sender.send_sms(contact, "Retry: Your notification is being resent.")
                elif channel.lower() == "whatsapp":
                    whatsapp_sender.send_whatsapp(contact, {"guest_name": guest_name})

                entry = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Guest Name": guest_name,
                    "Contact": contact,
                    "Channel": channel,
                    "Status": "Retried Successfully",
                    "ErrorMessage": "",
                }

                try:
                    google_sheets.add_notification_log(entry)
                except Exception as e:
                    safe_print(f"⚠️ Failed to write to Google Sheets: {e}")
                finally:
                    save_local_log(entry)

                safe_print(f"✅ Retry successful for {guest_name} on {channel}")
                break

            except Exception as e:
                safe_print(f"⚠️ Retry {attempt} failed for {guest_name} on {channel}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_FACTOR ** attempt)
                else:
                    entry = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Guest Name": guest_name,
                        "Contact": contact,
                        "Channel": channel,
                        "Status": "Retry Failed",
                        "ErrorMessage": str(e),
                    }
                    try:
                        google_sheets.add_notification_log(entry)
                    except Exception as gs_e:
                        safe_print(f"⚠️ Failed to log to Google Sheets: {gs_e}")
                    finally:
                        save_local_log(entry)

                    safe_print(f"❌ Permanent failure for {guest_name} on {channel}")

    safe_print("✅ Retry process complete.")
