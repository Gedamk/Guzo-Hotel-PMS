# guzo_backend/modules/email_handler.py
from modules.booking_handler import handle_booking
import email
import imaplib

def process_email_booking(subject, sender_email, body):
    """
    Email body format: "Hotel, Guest, Check-in, Check-out, Room"
    """
    try:
        hotel, guest, check_in, check_out, room = [x.strip() for x in body.split(",")]
        handle_booking(hotel, guest, check_in, check_out, room, source="Email", contact=sender_email)
        print("Booking received from Email ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")
    except Exception as e:
        print(f"Email Booking Error: {e}")
