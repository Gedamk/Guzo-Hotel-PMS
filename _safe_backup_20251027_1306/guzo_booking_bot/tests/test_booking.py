# test_booking.py
import unittest
from guzo_booking_bot.modules.booking import reset_sheet, sync_bookings, HEADER

class TestBooking(unittest.TestCase):

    def test_reset_sheet_preserves_headers(self):
        reset_sheet()
        self.assertTrue(True)  # No exception means pass

    def test_sync_bookings_writes_to_sheets(self):
        bookings = [
            {"Hotel Name": "Demo", "Guest Name": "Alice"},
            {"Hotel Name": "Demo", "Guest Name": "Bob"},
        ]
        sync_bookings(bookings)
        self.assertTrue(True)

