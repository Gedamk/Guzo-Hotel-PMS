# -*- coding: utf-8 -*-
"""
booking_confirmation_test.py
--------------------------------
This script tests end-to-end communication between:
1. Google Sheets booking entry (via google_sheets.py)
2. Email confirmation delivery (via email_sender.py)

It ensures that guest bookings added to the spreadsheet
trigger an email confirmation to the system inbox.
"""

import os
from dotenv import load_dotenv
from guzo_booking_bot.modules import google_sheets, email_sender

# Load environment variables safely
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env", override=True)

# Simulated test booking entry
sample_booking = {
    "Guest Name": "Selamawit Tadesse",
    "Source": "Telegram",
    "Check-In Date": "2025-10-31",
    "Nights": "2",
    "Room Type": "Deluxe Suite",
    "Rate Per Night(ETB)": "2500",
    "Revenue(ETB)": "5000",
    "Booking Status": "Confirmed",
    "Channel Ref": "Guzo Guest Assist",
    "Remark": "Auto-booked via bot",
    "Auto Reply": "Sent",
    "Handled By": "Guzo System",
    "Email": "owner@guzoassist.com",
    "Phone": "+251911000000"
}


def main():
    print("[INFO] Initializing Guzo Booking confirmation test...")
    try:
        # Step 1: Add to Google Sheet
        google_sheets.add_booking(sample_booking)
        print("[SUCCESS] Booking recorded for:", sample_booking["Guest Name"])

        # Step 2: Send confirmation email
        email_sender.send_booking_confirmation(
            recipient=sample_booking["Email"],
            guest_name=sample_booking["Guest Name"],
            checkin_date=sample_booking["Check-In Date"],
            nights=sample_booking["Nights"],
            room_type=sample_booking["Room Type"],
            revenue=sample_booking["Revenue(ETB)"],
        )
        print("[INFO] Email confirmation sent to", sample_booking["Email"])

    except Exception as e:
        print("[ERROR]", e)


if __name__ == "__main__":
    main()

