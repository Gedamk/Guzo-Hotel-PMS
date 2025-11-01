# -*- coding: utf-8 -*-
"""
auto_confirmation.py – Guzo Guest Assist (v11.1)
------------------------------------------------
Global hospitality-grade auto confirmation handler.

✨ Features:
• Bilingual (English + Amharic) confirmations
• Telegram + Email + WhatsApp/SMS support
• Auto-intent detection (booking / cancellation / general)
• Logs every action to Google Sheets
• Fully async + safe fallbacks
"""

import os, asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from guzo_booking_bot.modules import google_sheets, email_sender

# ------------------------------------------------------------------
# 🔧 Load environment variables
# ------------------------------------------------------------------
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ------------------------------------------------------------------
# 🌍 MULTILINGUAL MESSAGE BUILDER
# ------------------------------------------------------------------
def build_multilingual_message(intent: str, hotel_name: str) -> str:
    """Return a natural, bilingual (EN + AM) hospitality message."""
    today = datetime.now().strftime("%A, %B %d, %Y")

    if intent == "booking":
        eng = (
            f"🛎️ Thank you for choosing *{hotel_name}*.\n"
            "Your booking request has been received and is being processed.\n"
            "Our team will confirm your stay shortly.\n"
            f"📅 {today}"
        )
        amh = (
            f"🛎️ ስለ *{hotel_name}* መያዣዎ እናመሰግናለን። "
            "መያዣዎ ተቀባይነት አግኝቷል። በቅርቡ ይረጋገጣል።"
        )

    elif intent == "cancellation":
        eng = (
            f"❌ We’ve received your cancellation request for *{hotel_name}*.\n"
            "Your booking will be updated accordingly.\n"
            f"📅 {today}"
        )
        amh = (
            f"❌ የ*{hotel_name}* መሰረዝ ጥያቄዎን ተቀብያለን። "
            "መያዣዎ በቅርቡ ይዘምናል።"
        )

    else:
        eng = (
            f"💬 Thank you for contacting *{hotel_name}* via Guzo Guest Assist.\n"
            "Your message has been received and will be answered shortly.\n"
            f"📅 {today}"
        )
        amh = (
            f"💬 እናመሰግናለን። የ*{hotel_name}* ጥያቄዎ ተቀብያለን። "
            "በቅርቡ እንመልስልዎታለን።"
        )

    return f"{eng}\n\n{amh}\n\n— *Guzo Guest Assist*"


# ------------------------------------------------------------------
# 🎯 INTENT DETECTOR
# ------------------------------------------------------------------
def detect_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["book", "reserve", "stay", "room", "night"]):
        return "booking"
    if any(w in msg for w in ["cancel", "change", "modify", "reschedule"]):
        return "cancellation"
    return "general"


# ------------------------------------------------------------------
# 📧 EMAIL TEMPLATE RENDERER
# ------------------------------------------------------------------
def build_template_email(guest_name, hotel_name, message, template_name):
    """Load and personalize HTML email template."""
    try:
        path = os.path.join("guzo_booking_bot", "templates", template_name)
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        today = datetime.now().strftime("%A, %B %d, %Y")
        html = (
            html.replace("{{guest_name}}", guest_name)
            .replace("{{hotel_name}}", hotel_name)
            .replace("{{message}}", message)
            .replace("{{date}}", today)
            .replace("{{year}}", str(datetime.now().year))
        )
        return html
    except Exception as e:
        print(f"⚠️ Template rendering failed: {e}")
        return f"<p>Dear {guest_name}, your request for {hotel_name} has been received.</p>"


# ------------------------------------------------------------------
# 📨 TELEGRAM SENDER
# ------------------------------------------------------------------
async def send_telegram_message(chat_id: str, text: str):
    """Send a Telegram message asynchronously."""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        print(f"📱 Telegram sent → {chat_id}")
        return True
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return False


# ------------------------------------------------------------------
# 🤖 MAIN CONFIRMATION HANDLER
# ------------------------------------------------------------------
async def confirm_guest_request(guest_name, hotel_name, message, recipient_email=None):
    """Unified handler for booking/cancellation confirmations."""
    intent = detect_intent(message)
    print(f"📨 Processing {intent} confirmation for {guest_name} ({hotel_name})")

    # 1️⃣ Email confirmation
    email_status = "Not Sent"
    if recipient_email:
        try:
            template = (
                "booking_confirmation.html"
                if intent == "booking"
                else "cancellation_confirmation.html"
            )
            subject = f"Guzo Guest Assist – {'Booking' if intent=='booking' else 'Cancellation'} Confirmation"
            html_body = build_template_email(guest_name, hotel_name, message, template)
            success = email_sender.send_email(recipient_email, subject, html_body)
            email_status = "Email Sent" if success else "Email Failed"
            print(f"📧 {email_status} → {recipient_email}")
        except Exception as e:
            print(f"⚠️ Email send failed: {e}")
            email_status = "Email Failed"

    # 2️⃣ Telegram notification to hotel manager
    tg_status = "Not Sent"
    record = google_sheets.find_hotel_record(hotel_name)
    if record and "Telegram Chat ID" in record and record["Telegram Chat ID"]:
        chat_id = str(record["Telegram Chat ID"]).strip()
        text_msg = build_multilingual_message(intent, hotel_name)
        tg_success = await send_telegram_message(chat_id, text_msg)
        tg_status = "Telegram Sent" if tg_success else "Telegram Failed"

    # 3️⃣ SMS / WhatsApp fallback (if available)
    sms_status = "Not Sent"
    if record and "Phone" in record and record["Phone"]:
        phone = str(record["Phone"]).strip()
        text_msg = build_multilingual_message(intent, hotel_name)
        if hasattr(google_sheets, "send_sms_or_whatsapp"):
            sms_success = google_sheets.send_sms_or_whatsapp(phone, text_msg, channel="whatsapp")
            sms_status = "WhatsApp Sent" if sms_success else "WhatsApp Failed"

    # 4️⃣ Log result to Google Sheets
    final_status = f"{email_status}, {tg_status}, {sms_status}"
    google_sheets.log_new_request(guest_name, hotel_name, message, status=final_status)
    print(f"🗂️ Logged confirmation for {guest_name} ({hotel_name}) → {final_status}")

    return final_status


# ------------------------------------------------------------------
# 🧪 STANDALONE TEST
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("🔍 Testing multilingual auto confirmation module (v11.1)…")
    google_sheets.init_client()

    asyncio.run(
        confirm_guest_request(
            "Test Guest",
            "Sofi Hotel",
            "Need booking for 2 nights",
            "manager@sofihotel.com",
        )
    )
