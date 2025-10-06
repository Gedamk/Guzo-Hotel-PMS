# guzo_booking_bot/modules/whatsapp_sender.py
"""
WhatsApp Sender Module
Handles sending WhatsApp messages via Twilio with multilingual templates.
"""

import os
from twilio.rest import Client
from guzo_booking_bot import config

# Twilio setup
ACCOUNT_SID = config.TWILIO_ACCOUNT_SID
AUTH_TOKEN = config.TWILIO_AUTH_TOKEN
FROM_WHATSAPP = config.TWILIO_WHATSAPP_FROM

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# === Multilingual Templates ===
TEMPLATES = {
    "en": "🌍 Hello {guest}, your booking at {hotel} is {status}. Check-in: {check_in}, Check-out: {check_out}.",
    "am": "🌍 ሰላም {guest}፣ በ{hotel} ያደረጉት ቦታ ማረፊያ ሁኔታ ነው፡፡ መግቢያ: {check_in}, መውጫ: {check_out}።",
    "om": "🌍 Akkam {guest}, booking kee {hotel} irratti {status}. Check-in: {check_in}, Check-out: {check_out}.",
}

def send_whatsapp(to_number, placeholders, lang="en"):
    """
    Send WhatsApp to a guest.
    Uses multilingual templates (English, Amharic, Afaan Oromo).
    """
    try:
        if not to_number.startswith("+"):
            to_number = f"+251{to_number}" if len(to_number) == 9 else f"+{to_number}"

        template = TEMPLATES.get(lang, TEMPLATES["en"])
        body = template.format(**placeholders)

        msg = client.messages.create(
            body=body,
            from_=FROM_WHATSAPP,
            to=f"whatsapp:{to_number}"
        )
        print(f"✅ WhatsApp sent to {to_number}, SID: {msg.sid}")
        return msg.sid

    except Exception as e:
        print(f"❌ Failed to send WhatsApp to {to_number}: {e}")
        raise
