# -*- coding: utf-8 -*-
"""
Google Sheets → SQLite Backup Script
------------------------------------
Automatically syncs the 'Notifications Log' sheet into local storage/logs.db.
Can be run manually or scheduled (e.g., nightly via Task Scheduler).
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from guzo_booking_bot.modules import google_sheets

# ============================================================
# 🗂️ Setup local backup directory
# ============================================================
storage_dir = os.path.join(os.getcwd(), "storage")
os.makedirs(storage_dir, exist_ok=True)
db_path = os.path.join(storage_dir, "logs.db")

# ============================================================
# 🔄 Fetch all rows from Google Sheets
# ============================================================
print("📡 Fetching data from Google Sheets...")
try:
    sheet = google_sheets._open_sheet(
        google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
    )
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    print(f"✅ Loaded {len(df)} rows from Notifications Log.")
except Exception as e:
    print(f"❌ Failed to read from Google Sheets: {e}")
    exit(1)

# ============================================================
# 💾 Write or update SQLite database
# ============================================================
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications_backup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp TEXT,
            User TEXT,
            Lang TEXT,
            Sentiment TEXT,
            GuestMessage TEXT,
            BotReply TEXT
        )
    """)

    # Clear existing records before full sync
    cursor.execute("DELETE FROM notifications_backup")

    # Insert all fresh rows
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO notifications_backup
            (Timestamp, User, Lang, Sentiment, GuestMessage, BotReply)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row.get("Timestamp", ""),
            row.get("User", ""),
            row.get("Lang", ""),
            row.get("Sentiment", ""),
            row.get("Guest Message", ""),
            row.get("Bot Reply", "")
        ))

    conn.commit()
    conn.close()
    print(f"✅ Backup completed successfully at {datetime.now():%Y-%m-%d %H:%M:%S}")
except Exception as e:
    print(f"⚠️ SQLite backup failed: {e}")
