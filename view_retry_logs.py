# -*- coding: utf-8 -*-
"""
View Retry Logs
Displays retry logs stored in local SQLite backup.
"""

import sqlite3
from tabulate import tabulate
import sys, io

# Force UTF-8 safe output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

LOCAL_DB = "storage/logs.db"

def fetch_logs(limit=20):
    conn = sqlite3.connect(LOCAL_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, guest_name, contact, channel, status, error_message
        FROM retry_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def main():
    print("[INFO] Last Retry Logs (from local SQLite backup):\n")
    logs = fetch_logs()
    if logs:
        headers = ["Timestamp", "Guest", "Contact", "Channel", "Status", "Error"]
        print(tabulate(logs, headers=headers, tablefmt="grid"))
    else:
        print("[OK] No retry logs found.")

if __name__ == "__main__":
    main()

