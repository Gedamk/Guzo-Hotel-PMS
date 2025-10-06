# -*- coding: utf-8 -*-
"""
Retry Summary
Generates a daily summary of retry attempts and sends
a concise report to managers via Email + Telegram.
"""

import sqlite3
from datetime import datetime
from tabulate import tabulate
from guzo_booking_bot.modules import email_sender, telegram_sender

LOCAL_DB = "storage/logs.db"


def fetch_summary():
    """Fetch daily retry summary from local DB."""
    conn = sqlite3.connect(LOCAL_DB)
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("""
        SELECT channel, status, COUNT(*)
        FROM retry_logs
        WHERE date(timestamp) = ?
        GROUP BY channel, status
    """, (today,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "📊 Daily Retry Summary:\n\nNo retries needed today."

    table = tabulate(rows, headers=["Channel", "Status", "Count"], tablefmt="grid")
    return f"📊 Daily Retry Summary ({today}):\n\n{table}"


def send_summary():
    """Send summary report via email + telegram."""
    report = fetch_summary()

    # ✅ Centralized email sending
    email_sender.send_notification(
        "manager@guzoassist.com",
        "Daily Retry Summary",
        report
    )

    # Telegram alert
    telegram_sender.send_message(report)
    print("✅ Retry summary sent via Email & Telegram")


if __name__ == "__main__":
    send_summary()
