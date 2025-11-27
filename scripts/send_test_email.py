#!/usr/bin/env python
"""
Send a simple test booking confirmation email via SendGrid.

This is a standalone smoke-test script to verify that:
- .env is loaded correctly
- SENDGRID_API_KEY works
- email_confirmations.send_booking_confirmation_email works end-to-end
"""

import os
import sys

from dotenv import load_dotenv

# ----------------------------------------------------
# Ensure project root (.. from scripts/) is on sys.path
# ----------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now this import should work
from guzo_booking_bot.modules.email_confirmations import (
    send_booking_confirmation_email,
)


def main() -> None:
    # Load .env from project root
    load_dotenv()

    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    default_to = os.getenv("GUZO_TEST_EMAIL", "gedam_ka@yahoo.com")

    print(f"[TestEmail] SENDGRID_API_KEY present: {bool(sendgrid_key)}")
    print(f"[TestEmail] Sending to: {default_to}")

    to_emails = [default_to]

    ok = send_booking_confirmation_email(
        to_emails=to_emails,
        hotel_name=os.getenv("TEST_HOTEL_NAME", "Dream Big  Hotel"),
        property_code=os.getenv("TEST_PROPERTY_CODE", "DRE001"),
        guest_name="Test Guest (Smoke Test)",
        check_in="2025-11-28",
        check_out="2025-11-29",
        nights=1,
        total_amount_etb=0,
        payment_method="N/A",
        confirmation_id="TEST-EMAIL",
    )

    print(f"[TestEmail] Send OK: {ok}")


if __name__ == "__main__":
    main()
