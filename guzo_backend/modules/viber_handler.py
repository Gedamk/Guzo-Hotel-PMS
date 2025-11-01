# guzo_backend/modules/viber_handler.py
from modules.booking_handler import handle_booking

def handle_viber_message(sender_id, text):
    hotel, guest, check_in, check_out, room = [x.strip() for x in text.split(",")]
    handle_booking(hotel, guest, check_in, check_out, room, source="Viber", contact=sender_id)
    return "Booking received ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ"
