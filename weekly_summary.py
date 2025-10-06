# -*- coding: utf-8 -*-
"""
Weekly Summary
Generates a 7-day summary of retries and notifications,
delivers it to managers via Email + Telegram.
"""

import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from guzo_booking_bot.modules import email_sender, telegram_sender

LOCAL_DB = "storage/logs.db"


def fetch_weekly_summary():
    """Aggregate retry logs for the past 7 days."""
    conn = sqlite3.connect(LOCAL_DB)
    cur = conn.cursor()

    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cur.execute("""
        SELECT channel, status, COUNT(*)
        FROM retry_logs
        WHERE date(timestamp) >= ?
        GROUP BY channel, status
    """, (last_week,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "📊 Weekly Summary:\n\nNo retries or failed notifications in the past 7 days."

    table = tabulate(rows, headers=["Channel", "Status", "Count"], tablefmt="grid")
    return f"📊 Weekly Summary (last 7 days):\n\n{table}"


def send_weekly_summary():
    """Send weekly summary via email + telegram."""
    report = fetch_weekly_summary()

    # ✅ Centralized email sending
    email_sender.send_notification(
        "manager@guzoassist.com",
        "Weekly Retry Summary",
        report
    )

    telegram_sender.send_message(report)
    print("✅ Weekly summary sent via Email & Telegram")


if __name__ == "__main__":
    send_weekly_summary()
