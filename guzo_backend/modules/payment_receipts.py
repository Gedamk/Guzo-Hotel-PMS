# -*- coding: utf-8 -*-
"""
payment_receipts.py – Guzo Guest Assist Multilingual Payment Receipts
----------------------------------------------------------------------
Generates and sends multilingual payment receipts for Stripe, Telebirr,
and future PayPal transactions.

✅ UTF-8 safe and secure
✅ Auto-detects guest language from booking data
✅ Sends via Email, WhatsApp, and Telegram (manager alerts)
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from guzo_backend.modules import (
    email_sender,
    whatsapp_sender,
    telegram_notifier as telegram_sender,
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))
MANAGER_TELEGRAM_CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID", "5582570428")

# =====================================================
# Multilingual Receipt Templates
# =====================================================
TEMPLATES = {
    "en": (
        "Dear {guest_name},\n\n"
        "Your payment has been successfully processed.\n\n"
        "Provider: {provider}\n"
        "Amount: {amount}\n"
        "Status: {status}\n"
        "Reference: {reference}\n"
        "Date: {timestamp}\n\n"
        "Thank you for booking with Guzo Guest Assist!"
    ),
    "am": (
        "ውድ {guest_name},\n\n"
        "ክፍያዎ ተሳክቶ ተከናውኗል።\n\n"
        "አቅራቢ: {provider}\n"
        "መጠን: {amount}\n"
        "ሁኔታ: {status}\n"
        "መዝገብ ቁጥር: {reference}\n"
        "ቀን: {timestamp}\n\n"
        "ከGuzo Guest Assist ጋር ያስቀመጡትን በጣም እናመሰግናለን!"
    ),
    "om": (
        "Kabajamoo {guest_name},\n\n"
        "Kaffaltiin kee milkaa’een raawwatameera.\n\n"
        "Tajaajila: {provider}\n"
        "Hanga: {amount}\n"
        "Haala: {status}\n"
        "Lakkoofsa Fudhannaa: {reference}\n"
        "Guyyaa: {timestamp}\n\n"
        "Guzo Guest Assist waliin galma’uun kee galatoomaa!"
    ),
}

DEFAULT_LANGUAGE = "en"

# =====================================================
# Receipt Generator
# =====================================================
def generate_receipt(booking, provider, amount, currency, status, reference):
    """
    Build a receipt dictionary from booking and payment info.
    Auto-detects language from booking['Language'].
    """
    language = booking.get("Language", DEFAULT_LANGUAGE).lower()
    if language not in TEMPLATES:
        language = DEFAULT_LANGUAGE

    return {
        "guest_name": booking.get("Guest Name", "Guest"),
        "provider": provider.capitalize(),
        "amount": f"{amount:.2f} {currency.upper()}",
        "status": status.capitalize(),
        "reference": reference,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language": language,
        "contact_email": booking.get("Contact Email", ""),
        "contact_phone": booking.get("Contact Phone", ""),
    }

# =====================================================
# Receipt Dispatcher
# =====================================================
def send_receipt(receipt, manager_alert: bool = False):
    """
    Dispatch receipt via Email, WhatsApp, and optionally Telegram.
    """
    lang = receipt.get("language", DEFAULT_LANGUAGE)
    body = TEMPLATES[lang].format(**receipt)
    subject = f"Payment Receipt - {receipt['provider']} | Guzo Guest Assist"

    # --- Email ---
    if receipt.get("contact_email"):
        try:
            email_sender.send_email(receipt["contact_email"], subject, body)
            print(f"📧 Email receipt sent ({lang}) → {receipt['contact_email']}")
        except Exception as e:
            print(f"⚠️ Email sending failed: {e}")

    # --- WhatsApp ---
    if receipt.get("contact_phone"):
        try:
            msg = (
                f"Dear {receipt['guest_name']}, your payment of {receipt['amount']} "
                f"via {receipt['provider']} (Ref: {receipt['reference']}) has been processed. "
                "Thank you for booking with Guzo Guest Assist."
            )
            whatsapp_sender.send_whatsapp_message(receipt["contact_phone"], msg)
            print(f"📱 WhatsApp receipt sent → {receipt['contact_phone']}")
        except Exception as e:
            print(f"⚠️ WhatsApp sending failed: {e}")

    # --- Telegram Manager Alert ---
    if manager_alert:
        try:
            manager_msg = (
                f"🏨 *Payment Alert*\n\n"
                f"👤 Guest: {receipt['guest_name']}\n"
                f"💳 Provider: {receipt['provider']}\n"
                f"💰 Amount: {receipt['amount']}\n"
                f"📄 Status: {receipt['status']}\n"
                f"🔖 Ref: {receipt['reference']}\n"
                f"🕒 Date: {receipt['timestamp']}\n"
                f"🌐 Lang: {receipt['language'].upper()}"
            )
            telegram_sender.send_telegram_message(MANAGER_TELEGRAM_CHAT_ID, manager_msg)
            print(f"📨 Manager notified via Telegram → Chat ID {MANAGER_TELEGRAM_CHAT_ID}")
        except Exception as e:
            print(f"⚠️ Telegram manager alert failed: {e}")

# =====================================================
# Self-test (optional)
# =====================================================
if __name__ == "__main__":
    dummy_booking = {
        "Guest Name": "Test Guest",
        "Language": "en",
        "Contact Email": "guest@example.com",
        "Contact Phone": "+12025550123",
    }
    test_receipt = generate_receipt(
        booking=dummy_booking,
        provider="Stripe",
        amount=120.5,
        currency="USD",
        status="success",
        reference="TEST-12345",
    )
    send_receipt(test_receipt, manager_alert=True)
