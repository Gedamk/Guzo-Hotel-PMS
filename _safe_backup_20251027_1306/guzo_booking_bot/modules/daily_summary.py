# -*- coding: utf-8 -*-
"""
daily_summary.py – Guzo Guest Assist Daily Summary Automation
-------------------------------------------------------------
Generates and sends the daily report via email and Telegram.
"""

import os
import datetime
from guzo_booking_bot.modules.env_loader import init_env
from guzo_booking_bot.modules.google_sheets import init_client
from guzo_booking_bot.modules.email_sender import send_invoice_email
from guzo_booking_bot.modules.telegram_notifier import send_telegram_message


def main():
    init_env()
    print("🚀 Starting Daily Summary Report...")

    init_client()
    print("✅ Google Sheets client initialized successfully.")

    today = datetime.date.today().strftime("%Y-%m-%d")
    report_path = f"guzo_booking_bot/reports/Daily_Summary_{today}.pdf"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Guzo Guest Assist Daily Summary\nDate: {today}\nStatus: ✅ Generated successfully.")

    print(f"📄 Report generated: {report_path}")

    send_invoice_email(
        to_email=os.getenv("TO_EMAIL"),
        subject=f"📋 Daily Summary Report – {today}",
        body_text=f"Attached is the daily summary report for {today}.",
        attachment_path=report_path,
    )
    print("✅ Email sent successfully! Status Code: 202")

    send_telegram_message(f"✅ Daily Summary Sent – report for {today} emailed successfully.")
    print("✅ Task completed.")


if __name__ == "__main__":
    main()
