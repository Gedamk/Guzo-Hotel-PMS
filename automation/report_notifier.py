# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Report Notifier (v3.1)
------------------------------------------------------------
Runs automated weekly reports, emails them to management,
and sends Telegram notifications with success/failure status.

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Smart, simple, and scalable ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ aligned with Guzo's automation vision.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# --- Ensure root imports work ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from automation.report_generator import generate_report
from guzo_booking_bot.modules import email_sender
from guzo_booking_bot.modules.telegram_sender import send_telegram_message

# --- Load environment variables ---
load_dotenv()

MANAGER_EMAIL = os.getenv("EMAIL_RECEIVER", "manager@guzoassist.com")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
SENDER_EMAIL = os.getenv("EMAIL_SENDER", "reports@guzoassist.com")

def main():
    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Starting full report + notification pipeline...")

    try:
        # 1ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Generate the weekly report
        pdf_path = generate_report("Weekly")

        # 2ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Send email to management
        email_subject = "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly Performance Report"
        email_body = (
            "Dear Manager,\n\n"
            "Your latest weekly hospitality performance report has been generated.\n"
            "It includes updated KPIs, guest feedback sentiment, and AI insights.\n\n"
            "Please review the attached PDF for complete details.\n\n"
            "Best regards,\n"
            "Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Automated Hospitality System ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¤ÃÂÃÂÃÂÃÂ"
        )

        email_success = email_sender.send_email(
            to_email=MANAGER_EMAIL,
            subject=email_subject,
            body=email_body,  # ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ fixed argument name
            from_email=SENDER_EMAIL,
            attachments=[pdf_path],
        )

        # 3ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Prepare Telegram notification message
        now = datetime.now().strftime("%B %d, %Y %I:%M %p")

        if email_success:
            message = (
                f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ *Weekly Report Sent Successfully!*\n\n"
                f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {now}\n"
                f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Report: {os.path.basename(pdf_path)}\n"
                f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Delivered to: {MANAGER_EMAIL}"
            )
            print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Email + Telegram notification sent successfully.")
        else:
            message = (
                f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ *Report Email Failed!*\n\n"
                f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {now}\n"
                f"Report path: {pdf_path}\n"
                f"Please check SendGrid or Gmail settings."
            )
            print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Report email failed, notifying manager via Telegram only.")

        # 4ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Send Telegram notification (if ID configured)
        if MANAGER_CHAT_ID:
            try:
                send_telegram_message(MANAGER_CHAT_ID, message)
            except Exception as te:
                print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Telegram send failed: {te}")
        else:
            print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No MANAGER_CHAT_ID found ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ skipping Telegram notification.")

    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Unexpected error in report notifier: {e}")
        if MANAGER_CHAT_ID:
            try:
                send_telegram_message(MANAGER_CHAT_ID, f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Report notifier failed: {e}")
            except Exception as te:
                print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Telegram fallback failed: {te}")

if __name__ == "__main__":
    main()
