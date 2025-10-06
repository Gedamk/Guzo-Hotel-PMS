"""
web_booking.py
Handles booking submissions from the website.
"""

from modules.booking_handler import handle_booking

def handle_web_form(form_data):
    """
    Process website booking form.
    form_data: dict with keys: hotel_name, guest_name, check_in, check_out, room, contact
    """
    handle_booking(
        form_data["hotel_name"],
        form_data["guest_name"],
        form_data["check_in"],
        form_data["check_out"],
        form_data["room"],
        source="Website",
        contact=form_data.get("contact", ""),
    )
