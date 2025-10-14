# guest_notifications.py
"""
Fetch new bookings and notify hotels using email + SMS.
"""

from guzo_booking_bot.modules import google_sheets
from guzo_booking_bot.modules import email_sender
from guzo_booking_bot.modules import sms_service

def _compose_booking_message(booking: dict) -> str:
    """Create a concise booking summary message."""
    return (
        f"New booking for {booking.get('Hotel name') or booking.get('hotel_name')}\n"
        f"Guest: {booking.get('Guest Name') or booking.get('guest_name')}\n"
        f"Check-in: {booking.get('Check-in') or booking.get('check_in')}\n"
        f"Check-out: {booking.get('Check-out') or booking.get('check_out')}\n"
        f"Room: {booking.get('Room') or booking.get('room')}\n"
        f"Contact: {booking.get('Contact') or booking.get('contact')}\n"
    )

def notify_hotels_about_new_bookings():
    print("ÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂ´ÃÂÃÂÃÂÃÂ Checking for new bookings...")
    bookings = google_sheets.get_new_guest_bookings()
    if not bookings:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No new bookings found.")
        return

    hotel_contacts = google_sheets.get_hotel_contacts()
    if not hotel_contacts:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No hotel contacts available.")
        return

    for booking in bookings:
        guest_name = booking.get("Guest Name") or booking.get("guest_name")
        hotel_name = booking.get("Hotel name") or booking.get("hotel_name")
        if not hotel_name:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Booking without hotel name for guest {guest_name}. Skipping.")
            continue

        # Find hotel contact (case-insensitive)
        contact = None
        for h in hotel_contacts:
            if (h.get("Hotel name") or h.get("Hotel name", "")).strip().lower() == hotel_name.strip().lower():
                contact = h
                break

        if not contact:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No contact found for {hotel_name}. Skipping notification.")
            continue

        message = _compose_booking_message(booking)

        # 1) Try email
        email_sent = False
        hotel_email = contact.get("email")
        if hotel_email:
            try:
                subject = f"New Booking ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {hotel_name}"
                email_sender.send_email(hotel_email, subject, message)
                email_sent = True
            except Exception as e:
                print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Email failed for {hotel_email}: {e}")

        # 2) Try SMS (fallback or additional)
        sms_sent = False
        hotel_phone = contact.get("phone") or contact.get("Phone") or booking.get("Contact")
        if hotel_phone:
            sms_result = sms_service.send_sms(hotel_phone, message, via_whatsapp=True)
            if sms_result.get("ok"):
                sms_sent = True
            else:
                print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ SMS failed for {hotel_phone}: {sms_result.get('error')}")

        # Final: update booking status in sheet
        if email_sent or sms_sent:
            google_sheets.update_booking_status(guest_name, status="Notified")
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Notified {hotel_name} for booking by {guest_name}")
        else:
            # if no method worked, leave status as is or set to 'Attempted'
            google_sheets.update_booking_status(guest_name, status="Attempted")
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ All notification methods failed for booking of {guest_name} at {hotel_name}")

if __name__ == "__main__":
    notify_hotels_about_new_bookings()
