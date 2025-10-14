"""
Helper script to add a test booking into the GuestAssist Google Sheet.
"""

import random
from datetime import datetime, timedelta
from guzo_booking_bot.modules.google_sheets import add_guest_booking

# Some sample data for random bookings
HOTELS = ["Sofi Hotel", "Lalibela Lodge", "Addis View Hotel", "Blue Nile Resort"]
GUESTS = ["John Doe", "Jane Smith", "Michael Brown", "Sarah Johnson", "David Miller"]
ROOM_TYPES = ["Single", "Double", "Suite"]

def generate_random_booking():
    hotel_name = random.choice(HOTELS)
    guest_name = random.choice(GUESTS)
    today = datetime.now()
    check_in = today.strftime("%Y-%m-%d")
    check_out = (today + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
    room = random.choice(ROOM_TYPES)
    source = random.choice(["Email", "WhatsApp", "Telegram", "Website"])
    contact = f"{guest_name.lower().replace(' ', '.')}@example.com"

    booking = {
        "hotel_name": hotel_name,
        "guest_name": guest_name,
        "check_in": check_in,
        "check_out": check_out,
        "room": room,
        "source": source,
        "contact": contact,
        "status": "New",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "retry_count": 0,
        "last_attempt": ""
    }
    return booking


if __name__ == "__main__":
    booking = generate_random_booking()
    print(f"Ã°ÂÂÂ Adding test booking: {booking}")
    add_guest_booking(booking)
