# guzo_booking_bot/dispatcher.py
"""
Dispatcher Module
Handles sending notifications via Email ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ SMS ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ WhatsApp ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram,
with fallbacks and logging into Google Sheets.
"""

from guzo_booking_bot.modules import (
    email_sender, sms_sender, whatsapp_sender, telegram_sender, google_sheets
)
from datetime import datetime
import re

def is_valid_email(email):
    return bool(email and re.match(r"[^@]+@[^@]+\.[^@]+", email))

def is_phone_number(value):
    return bool(value and str(value).isdigit() and (9 <= len(value) <= 15))

def dispatch_notification(guest_name, contact, subject, html_body,
                          guest_type="standard", language="en"):
    """Try sending notification across channels with fallback + log."""
    sent = False
    errors = []

    # 1. Try Email
    if is_valid_email(contact):
        try:
            email_sender.send_email(contact, subject, html_body)
            google_sheets.add_notification_log({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Guest Name": guest_name,
                "Guest Type": guest_type,
                "Language": language,
                "Contact": contact,
                "Channel": "Email",
                "Status": "Success",
            })
            return True
        except Exception as e:
            errors.append(f"Email failed: {e}")

    # 2. Try SMS
    if is_phone_number(contact):
        try:
            sms_sender.send_sms(contact, f"Guzo Assist: Dear {guest_name}, check your booking update.")
            google_sheets.add_notification_log({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Guest Name": guest_name,
                "Guest Type": guest_type,
                "Language": language,
                "Contact": contact,
                "Channel": "SMS",
                "Status": "Success",
            })
            return True
        except Exception as e:
            errors.append(f"SMS failed: {e}")

    # 3. Try WhatsApp
    if is_phone_number(contact):
        try:
            whatsapp_sender.send_whatsapp(contact, {"guest_name": guest_name}, lang=language)
            google_sheets.add_notification_log({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Guest Name": guest_name,
                "Guest Type": guest_type,
                "Language": language,
                "Contact": contact,
                "Channel": "WhatsApp",
                "Status": "Success",
            })
            return True
        except Exception as e:
            errors.append(f"WhatsApp failed: {e}")

    # 4. Escalate ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram Manager Alert
    try:
        telegram_sender.send_message(
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Escalation Needed\nGuest: {guest_name}\nContact: {contact}\nErrors: {'; '.join(errors)}"
        )
    except Exception as e:
        errors.append(f"Telegram failed: {e}")

    # Log final failure
    google_sheets.add_notification_log({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Guest Name": guest_name,
        "Guest Type": guest_type,
        "Language": language,
        "Contact": contact,
        "Channel": "System",
        "Status": "Escalation Needed",
        "ErrorMessage": "; ".join(errors)
    })

    return False
