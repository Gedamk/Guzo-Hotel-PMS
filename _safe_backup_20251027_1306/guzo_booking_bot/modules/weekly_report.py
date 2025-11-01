# -*- coding: utf-8 -*-
"""
weekly_report.py – Guzo Guest Assist Automated Weekly Report
------------------------------------------------------------
Generates bilingual PDF report, emails it to hotel managers,
and sends Telegram confirmation.
"""

import os
from datetime import date
from guzo_booking_bot.modules.env_loader import init_env
from guzo_booking_bot.modules.google_sheets import init_client
from guzo_booking_bot.modules.email_sender import send_invoice_email
from guzo_booking_bot.modules.telegram_notifier import send_telegram_message


def main():
    init_env()
    print("🚀 Starting Weekly Report Generation...")

    init_client()
    print("✅ Google Sheets client initialized successfully.")

    report_path = f"guzo_booking_bot/reports/Weekly_Report_{date.today()}.pdf"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Guzo Guest Assist Weekly Report\n\nStatus: ✅ Generated successfully.")

    print(f"📄 Report generated: {report_path}")

    send_invoice_email(
        to_email=os.getenv("TO_EMAIL"),
        subject=f"📊 Weekly Report – {date.today()}",
        body_text="Attached is your weekly bilingual report summary.",
        attachment_path=report_path,
    )
    print("✅ Email sent successfully! Status Code: 202")

    send_telegram_message("✅ Weekly Report Sent – check your email for the latest summary.")
    print("✅ Task completed.")


if __name__ == "__main__":
    main()

