"""
Booking Handler
- Logs bookings
- Sends notifications via Email, SMS, WhatsApp, Telegram, Viber
"""

from guzo_booking_bot.modules.booking import log_booking
from guzo_booking_bot.modules import notifications as notify
from guzo_booking_bot import config as cfg
import logging
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# -----------------------
# Utility Helpers
# -----------------------

def is_email(contact: str) -> bool:
    """Check if contact string is an email address"""
    return bool(contact and "@" in str(contact))


def format_phone(contact: str) -> str:
    """
    Normalize phone number to E.164 (+251...)
    Rules:
    - If already starts with +, assume correct
    - If starts with 0XXXXXXXX, replace leading 0 with +251
    - Otherwise, return as-is (may fail if invalid)
    """
    if not contact:
        return ""

    contact = str(contact).strip()

    if contact.startswith("+"):
        return contact
    if contact.startswith("0") and len(contact) >= 9:
        return "+251" + contact[1:]  # e.g. 0911xxxxxx → +251911xxxxxx
    return contact


def is_phone(contact: str) -> bool:
    """Check if contact looks like a phone number in E.164 format"""
    return bool(contact and re.match(r"^\+\d{7,15}$", contact))


# -----------------------
# Booking Handler
# -----------------------

def handle_booking(data: dict):
    """
    Handles a new booking:
    1. Logs the booking
    2. Sends notifications to guest and hotel staff

    data keys must match HEADER in booking.py:
    'Hotel Name', 'Guest Name', 'Check-in', 'Check-out', 'Room',
    'Source', 'Contact', 'Status', 'Timestamp'
    """
    guest_name = data.get("Guest Name", "Unknown")
    contact = str(data.get("Contact", "")).strip()

    # 1️⃣ Log booking to Google Sheets
    log_booking(
        hotel_name=data.get("Hotel Name"),
        guest_name=guest_name,
        check_in=data.get("Check-in"),
        check_out=data.get("Check-out"),
        room=data.get("Room"),
        source=data.get("Source"),
        contact=contact,
        status=data.get("Status", "Pending"),
        timestamp=data.get("Timestamp")
    )
    logger.info(f"✅ Booking synced: {data}")

    # 2️⃣ Prepare notification message
    message = (
        f"📢 New Booking Alert!\n\n"
        f"🏨 Hotel: {data.get('Hotel Name')}\n"
        f"👤 Guest: {guest_name}\n"
        f"📅 Check-in: {data.get('Check-in')}\n"
        f"📅 Check-out: {data.get('Check-out')}\n"
        f"🛏️ Room: {data.get('Room')}\n"
        f"🔗 Source: {data.get('Source')}\n"
        f"📌 Status: {data.get('Status', 'Pending')}"
    )

    # 3️⃣ Send Email if contact is email
    if is_email(contact):
        notify.send_email(to_email=contact, subject="Booking Confirmation", body=message, guest_name=guest_name)

    # 4️⃣ Send SMS / WhatsApp if contact is phone
    phone = format_phone(contact)
    if is_phone(phone):
        notify.send_sms(to_phone=phone, message=message, guest_name=guest_name)
        notify.send_whatsapp(to_phone=phone, message=message, guest_name=guest_name)

    # 5️⃣ Send Telegram notification (requires chat_id)
    if cfg.TELEGRAM_TOKEN and data.get("TelegramChatID"):
        notify.send_telegram(chat_id=data.get("TelegramChatID"), message=message, guest_name=guest_name)

    # 6️⃣ Send Viber notification (if enabled & phone contact)
    if cfg.VIBER_API_KEY and is_phone(phone):
        notify.send_viber(to_phone=phone, message=message, guest_name=guest_name)

