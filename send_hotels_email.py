# -*- coding: utf-8 -*-
"""
Send Hotels Email
Handles sending booking notifications to guests across multiple channels,
with seasonality-based offers and escalation.
"""

from guzo_booking_bot.modules import google_sheets, email_sender, template_loader
from guzo_booking_bot.modules import sms_sender, whatsapp_sender
from guzo_booking_bot.modules import seasonality_engine
from guzo_booking_bot.modules import telegram_sender
import re
from datetime import datetime
import sys, io

# Force UTF-8 safe output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# =========================
# SUBJECTS & TEMPLATES
# =========================
SUBJECTS = {
    "confirmed": "Booking Confirmation - Guzo Guest Assist",
    "cancelled": "Booking Update - Guzo Guest Assist",
    "modified": "Booking Update - Guzo Guest Assist",
    "paid": "Payment Receipt - Guzo Guest Assist",
    "special_offer": "Exclusive Offer - Guzo Guest Assist",
}
TEMPLATES = {
    "confirmed": "booking_confirmation.html",
    "cancelled": "booking_update.html",
    "modified": "booking_update.html",
    "paid": "payment_receipt.html",
    "special_offer": "special_offer.html",
}

# =========================
# HELPERS
# =========================
def is_valid_email(email):
    return bool(email and re.match(r"[^@]+@[^@]+\.[^@]+", str(email).strip()))

def is_phone_number(value):
    value = str(value).strip()
    return value.isdigit() and (9 <= len(value) <= 15)

def generate_receipt_number(guest_name, timestamp=""):
    safe_guest = (guest_name or "GST").replace(" ", "").upper()[:3]
    ts = datetime.now().strftime("%Y%m%d%H%M")
    return f"RCP-{safe_guest}-{ts}"

def log_notification(guest_name, contact, channel, status, error="", guest_type="standard", language="en"):
    """Log results into NotificationsLog sheet"""
    google_sheets.add_notification_log({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Guest Name": guest_name,
        "Guest Type": guest_type,
        "Language": language,
        "Contact": contact,
        "Channel": channel,
        "Status": status,
        "ErrorMessage": error,
    })

# =========================
# MAIN
# =========================
def main():
    try:
        bookings = google_sheets.get_guest_assist()
        print(f"[OK] Loaded {len(bookings)} bookings from Guest Assist.")
    except Exception as e:
        print(f"[FAIL] Could not load bookings: {e}")
        return

    for booking in bookings:
        guest_name = booking.get("Guest Name", "Guest")
        contact = str(booking.get("Contact", "")).strip()
        status = str(booking.get("Status", "pending")).lower()
        guest_type = str(booking.get("Guest Type", "standard")).lower()
        language = str(booking.get("Language", "en")).lower()

        subject = SUBJECTS.get(status, "Booking Update - Guzo Guest Assist")
        template = TEMPLATES.get(status, "booking_update.html")

        placeholders = {
            "guest_name": guest_name,
            "hotel_name": booking.get("Hotel Name", "Our Partner Hotel"),
            "check_in": booking.get("Check-in", "N/A"),
            "check_out": booking.get("Check-out", "N/A"),
            "room_type": booking.get("Room", "Standard"),
            "guest_count": booking.get("Guest Count", "1"),
            "booking_source": booking.get("Source", "Direct"),
            "booking_status": status.capitalize(),
            "booking_reference": booking.get("Timestamp", "N/A"),
            "manage_booking_url": "https://guzoassist.com/manage"
        }

        if status == "paid":
            placeholders.update({
                "receipt_number": booking.get("Receipt Number") or generate_receipt_number(guest_name),
                "payment_date": booking.get("Payment Date", datetime.now().strftime("%Y-%m-%d")),
                "payment_amount": booking.get("Payment Amount", "N/A"),
                "payment_method": booking.get("Payment Method", "Telebirr"),
            })

        html_body = template_loader.load_template(template, placeholders)

        # =======================
        # CHANNEL LOGIC
        # =======================
        sent = False

        # VIP guests → try ALL channels
        if guest_type == "vip":
            if is_valid_email(contact):
                try:
                    email_sender.send_email(contact, subject, html_body)
                    log_notification(guest_name, contact, "Email", "Success", guest_type, language)
                    sent = True
                except Exception as e:
                    log_notification(guest_name, contact, "Email", "Failed", str(e), guest_type, language)
            if is_phone_number(contact):
                try:
                    sms_sender.send_sms(contact, f"[VIP] Dear {guest_name}, your booking is {status}.")
                    log_notification(guest_name, contact, "SMS", "Success", guest_type, language)
                except Exception as e:
                    log_notification(guest_name, contact, "SMS", "Failed", str(e), guest_type, language)
                try:
                    whatsapp_sender.send_whatsapp(contact, placeholders, lang=language)
                    log_notification(guest_name, contact, "WhatsApp", "Success", guest_type, language)
                except Exception as e:
                    log_notification(guest_name, contact, "WhatsApp", "Failed", str(e), guest_type, language)
            continue

        # International guests → Email preferred, WhatsApp fallback
        if guest_type == "international":
            if is_valid_email(contact):
                try:
                    email_sender.send_email(contact, subject, html_body)
                    log_notification(guest_name, contact, "Email", "Success", guest_type, language)
                    sent = True
                except Exception as e:
                    log_notification(guest_name, contact, "Email", "Failed", str(e), guest_type, language)
            if not sent and is_phone_number(contact):
                try:
                    whatsapp_sender.send_whatsapp(contact, placeholders, lang=language)
                    log_notification(guest_name, contact, "WhatsApp", "Success", guest_type, language)
                    sent = True
                except Exception as e:
                    log_notification(guest_name, contact, "WhatsApp", "Failed", str(e), guest_type, language)

        # Local guests → WhatsApp preferred, SMS fallback, Email last
        else:
            if is_phone_number(contact):
                try:
                    whatsapp_sender.send_whatsapp(contact, placeholders, lang=language)
                    log_notification(guest_name, contact, "WhatsApp", "Success", guest_type, language)
                    sent = True
                except Exception as e:
                    log_notification(guest_name, contact, "WhatsApp", "Failed", str(e), guest_type, language)
                if not sent:
                    try:
                        sms_sender.send_sms(contact, f"Guzo Guest Assist: Dear {guest_name}, your booking is {status}.")
                        log_notification(guest_name, contact, "SMS", "Success", guest_type, language)
                        sent = True
                    except Exception as e:
                        log_notification(guest_name, contact, "SMS", "Failed", str(e), guest_type, language)
            elif is_valid_email(contact):
                try:
                    email_sender.send_email(contact, subject, html_body)
                    log_notification(guest_name, contact, "Email", "Success", guest_type, language)
                except Exception as e:
                    log_notification(guest_name, contact, "Email", "Failed", str(e), guest_type, language)

        # Escalation if all failed
        if not sent:
            log_notification(guest_name, contact, "System", "Escalation Needed", "All channels failed", guest_type, language)
            print(f"[ALERT] Escalation needed for {guest_name} (contact: {contact})")

        # =======================
        # SEASONAL SPECIAL OFFERS
        # =======================
        try:
            occupancy_rate = int(booking.get("Occupancy", 60))
            special_offer = seasonality_engine.generate_offer(
                booking.get("Hotel Name", "Our Partner Hotel"),
                occupancy_rate
            )

            if special_offer and is_valid_email(contact):
                offer_html = template_loader.load_template("special_offer.html", {
                    "guest_name": guest_name,
                    "hotel_name": special_offer["hotel_name"],
                    "offer_title": special_offer["offer_title"],
                    "offer_discount": special_offer["offer_discount"],
                    "offer_valid_until": special_offer["offer_valid_until"],
                    "intl_season": special_offer["intl_season"],
                    "eth_season": special_offer["eth_season"],
                })
                email_sender.send_email(contact, SUBJECTS["special_offer"], offer_html)
                log_notification(guest_name, contact, "Email", "Success (Special Offer)", guest_type, language)
                print(f"[OK] Special offer sent to {guest_name} ({contact}) → {special_offer['offer_discount']}% OFF")

                # Telegram alert for manager
                manager_msg = (
                    f"[INFO] Special Offer Triggered\n\n"
                    f"Hotel: {special_offer['hotel_name']}\n"
                    f"Guest: {guest_name}\n"
                    f"Discount: {special_offer['offer_discount']}%\n"
                    f"Valid Until: {special_offer['offer_valid_until']}\n"
                    f"Occupancy Rate: {occupancy_rate}%\n\n"
                    f"International Season: {special_offer['intl_season']}\n"
                    f"Ethiopian Season: {special_offer['eth_season']}"
                )
                telegram_sender.send_telegram_message("5582570428", manager_msg)
        except Exception as e:
            print(f"[WARN] Could not process special offer for {guest_name}: {e}")

if __name__ == "__main__":
    main()
