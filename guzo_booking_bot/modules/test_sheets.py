# guzo_booking_bot/modules/test_sheets.py
"""
Test script for Google Sheets integration.
"""

from . import google_sheets  # ✅ relative import avoids circular import

def test_guest_assist_access():
    """Test reading from GuestAssist Google Sheet."""
    try:
        new_bookings = google_sheets.get_new_guest_bookings()
        print("✅ GuestAssist Sheet Access Success!")
        print(f"Found {len(new_bookings)} NEW bookings.")
        for r in new_bookings[:5]:  # print first 5 rows
            print(r)
    except Exception as e:
        print("❌ Failed to access GuestAssist Sheet:", e)

def test_hotel_contacts_access():
    """Test reading from Hotel Contacts Google Sheet."""
    try:
        contacts = google_sheets.get_hotel_contacts()
        print("✅ Hotel Contacts Sheet Access Success!")
        print(f"Found {len(contacts)} hotel contacts.")
        for c in contacts[:5]:  # print first 5 rows
            print(c)
    except Exception as e:
        print("❌ Failed to access Hotel Contacts Sheet:", e)

if __name__ == "__main__":
    test_guest_assist_access()
    test_hotel_contacts_access()
