# test_hotel_directory.py
import unittest
from guzo_backend.modules.hotel_directory import get_hotel_contact, load_hotels

class TestHotelDirectory(unittest.TestCase):

    def test_get_hotel_contact(self):
        contact = get_hotel_contact("Demo Hotel")
        self.assertEqual(contact, "12345")

    def test_load_hotels_returns_list(self):
        hotels = load_hotels()
        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0]["name"], "Demo Hotel")
