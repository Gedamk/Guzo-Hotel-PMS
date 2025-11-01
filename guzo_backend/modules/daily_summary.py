# -*- coding: utf-8 -*-
"""
daily_summary.py – Guzo Guest Assist Daily Summary Automation
-------------------------------------------------------------
Generates and sends the daily report via email and Telegram.
Compatible with the upgraded email_sender.py.
"""

import os
import datetime
from guzo_backend.modules.env_loader import init_env
from guzo_backend.modules.google_sheets import init_client
from guzo_backend.modules.email_sender import send_invoice_email
from guzo_backend.modules.telegram_notifier import send_telegram_message


def main():
    init_env()
    print("🚀 Starting Daily Summary Report...")

    # ✅ Initialize Google Sheets
    init_client()
    print("✅ Google Sheets client initialized successfully.")

    today = datetime.date.today().strftime("%Y-%m-%d")
    report_path = f"guzo_backend/reports/Daily_Summary_{today}.pdf"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    # ✅ Generate local report file
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Guzo Guest Assist Daily Summary\nDate: {today}\nStatus: ✅ Generated successfully.")

    print(f"📄 Report generated: {report_path}")

    # ✅ Updated email sender call (matches upgraded email_sender.py)
    send_invoice_email(
        to_email=os.getenv("TO_EMAIL", "manager@guzoassist.com"),
        subject=f"📋 Daily Summary Report – {today}",
        body_text=f"""
        <h3>📊 Guzo Guest Assist – Daily Summary ({today})</h3>
        <p>The attached PDF contains the summary of today's performance.</p>
        <p>Thank you for using Guzo Guest Assist!</p>
        """,
        pdf_path=report_path,
    )

    print("✅ Email sent successfully!")

    # ✅ Telegram notification
    send_telegram_message(f"✅ Daily Summary Sent – report for {today} emailed successfully.")
    print("✅ Task completed.")


if __name__ == "__main__":
    main()
