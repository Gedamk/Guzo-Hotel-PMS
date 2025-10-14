# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly Report Email Scheduler
----------------------------------------------------
Automatically generates and emails the weekly PDF report
every Friday at 8:00 AM using SendGrid.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# --- Fix Python import path ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from automation.report_generator import generate_report  # ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ now works
from guzo_booking_bot.modules import email_sender

load_dotenv()


def send_weekly_report():
    """Generate and email the weekly performance report."""
    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Starting automated weekly report generation...")

    try:
        # 1ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Generate the report
        pdf_path = generate_report("Weekly")

        # 2ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Prepare email
        subject = f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Guzo Guest Assist Weekly Report ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {datetime.now().strftime('%B %d, %Y')}"
        body = (
            "Dear Manager,\n\n"
            "Please find attached your weekly hospitality performance report.\n"
            "This includes KPIs, AI insights, and occupancy trends.\n\n"
            "Warm regards,\n"
            "Guzo Guest Assist Automation System"
        )

        receiver = os.getenv("EMAIL_RECEIVER", "manager@guzoassist.com")

        # 3ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Send email via SendGrid
        email_sender.send_email(
            to_email=receiver,
            subject=subject,
            body=body,
            attachments=[pdf_path]
        )

        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Weekly report emailed successfully to {receiver}!")

    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to send weekly report: {e}")


if __name__ == "__main__":
    send_weekly_report()
