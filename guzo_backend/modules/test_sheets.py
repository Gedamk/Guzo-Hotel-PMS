# guzo_backend/modules/test_sheets.py
"""
Test script for Google Sheets integration.
"""

from . import google_sheets  # ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ relative import avoids circular import

def test_guest_assist_access():
    """Test reading from GuestAssist Google Sheet."""
    try:
        new_bookings = google_sheets.get_new_guest_bookings()
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ GuestAssist Sheet Access Success!")
        print(f"Found {len(new_bookings)} NEW bookings.")
        for r in new_bookings[:5]:  # print first 5 rows
            print(r)
    except Exception as e:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to access GuestAssist Sheet:", e)

def test_hotel_contacts_access():
    """Test reading from Hotel Contacts Google Sheet."""
    try:
        contacts = google_sheets.get_hotel_contacts()
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Hotel Contacts Sheet Access Success!")
        print(f"Found {len(contacts)} hotel contacts.")
        for c in contacts[:5]:  # print first 5 rows
            print(c)
    except Exception as e:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to access Hotel Contacts Sheet:", e)

if __name__ == "__main__":
    test_guest_assist_access()
    test_hotel_contacts_access()
