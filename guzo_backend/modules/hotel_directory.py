# guzo_backend/modules/hotel_directory.py
HOTELS = [
    {"name": "Demo Hotel", "contact": "12345"},
]

def get_hotel_contact(hotel_name):
    for h in HOTELS:
        if h["name"] == hotel_name:
            return h["contact"]
    return None

def load_hotels():
    return HOTELS
