# guzo_booking_bot/modules/whatsapp_handler.py
from modules.booking_handler import handle_booking

def handle_whatsapp_message(sender_number, text):
    """
    Expected format: "Hotel, Guest, Check-in, Check-out, Room"
    """
    try:
        hotel, guest, check_in, check_out, room = [x.strip() for x in text.split(",")]
        handle_booking(hotel, guest, check_in, check_out, room, source="WhatsApp", contact=sender_number)
        return "Booking received ✅"
    except Exception as e:
        return f"Error: {e}"
