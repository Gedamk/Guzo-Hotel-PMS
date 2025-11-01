# -*- coding: utf-8 -*-
"""
Payment Receipts
Generates and sends multilingual receipts for all payment providers.
Auto-detects guest language from booking data.
Supports Email, WhatsApp, and Telegram notifications.
"""

from datetime import datetime
from guzo_booking_bot.modules import email_sender, whatsapp_sender, telegram_sender

# ==============================
# Multilingual Templates
# ==============================
TEMPLATES = {
    "en": (
        "Dear {guest_name},\n\n"
        "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Your payment has been processed.\n\n"
        "Provider: {provider}\n"
        "Amount: {amount}\n"
        "Status: {status}\n"
        "Reference: {reference}\n"
        "Date: {timestamp}\n\n"
        "Thank you for booking with Guzo Guest Assist!"
    ),
    "am": (
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµ {guest_name},\n\n"
        "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ«ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ³ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ·ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢\n\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­: {provider}\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ: {amount}\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ³: {status}\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ»: {reference}\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ: {timestamp}\n\n"
        "ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨Guzo Guest Assist ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ!"
    ),
    "om": (
        "Kabajamoo {guest_name},\n\n"
        "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Kaffaltiin kee milkaa'ee raawwatameera.\n\n"
        "Ogeessa Tajaajilaa: {provider}\n"
        "Hanga: {amount}\n"
        "Haala: {status}\n"
        "Lakkoofsa Fudhannaa: {reference}\n"
        "Guyyaa: {timestamp}\n\n"
        "Guzo Guest Assist waliin galma'uu kee galatoomaa!"
    ),
}

DEFAULT_LANGUAGE = "en"

# ==============================
# Receipt Generator
# ==============================
def generate_receipt(booking, provider, amount, currency, status, reference):
    """
    Build a receipt dictionary using booking record + payment info.
    Auto-detects language from booking['Language'].
    """
    language = booking.get("Language", DEFAULT_LANGUAGE).lower()
    if language not in TEMPLATES:
        language = DEFAULT_LANGUAGE

    return {
        "guest_name": booking.get("Guest Name", "Guest"),
        "provider": provider.capitalize(),
        "amount": f"{amount:.2f} {currency.upper()}",
        "status": status,
        "reference": reference,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language": language,
        "contact_email": booking.get("Contact Email", ""),
        "contact_phone": booking.get("Contact Phone", ""),
    }


# ==============================
# Receipt Dispatcher
# ==============================
def send_receipt(receipt, manager_alert=False):
    """
    Send receipt across Email, WhatsApp, and (optionally) Telegram.
    """
    lang = receipt.get("language", DEFAULT_LANGUAGE)
    body = TEMPLATES[lang].format(**receipt)
    subject = f"Payment Receipt - {receipt['provider']} - Guzo Guest Assist"

    # --- Email ---
    if receipt.get("contact_email"):
        try:
            email_sender.send_email(receipt["contact_email"], subject, body)
            print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Receipt sent via Email ({lang}) to {receipt['contact_email']}")
        except Exception as e:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Email receipt failed: {e}")

    # --- WhatsApp ---
    if receipt.get("contact_phone"):
        try:
            whatsapp_sender.send_whatsapp(receipt["contact_phone"], {
                "guest_name": receipt["guest_name"],
                "message": f"Payment confirmed: {receipt['amount']} via {receipt['provider']} (Ref: {receipt['reference']})"
            })
            print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ± Receipt sent via WhatsApp to {receipt['contact_phone']}")
        except Exception as e:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ WhatsApp receipt failed: {e}")

    # --- Telegram (Manager Alert) ---
    if manager_alert:
        try:
            manager_msg = (
                f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ *Payment Alert*\n\n"
                f"Guest: {receipt['guest_name']}\n"
                f"Provider: {receipt['provider']}\n"
                f"Amount: {receipt['amount']}\n"
                f"Status: {receipt['status']}\n"
                f"Reference: {receipt['reference']}\n"
                f"Date: {receipt['timestamp']}\n"
                f"Language: {receipt['language'].upper()}"
            )
            telegram_sender.send_telegram_message("5582570428", manager_msg)
            print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Manager notified via Telegram")
        except Exception as e:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram manager alert failed: {e}")
