# -*- coding: utf-8 -*-
"""
auto_confirmation.py – Guzo Guest Assist (v12.1)
------------------------------------------------
Handles multilingual confirmations, email + Telegram
notifications, and unified logging to hotel + central sheets.
"""

import os
import random
import asyncio
import datetime
from dotenv import load_dotenv
from telegram import Bot
from guzo_backend.modules import google_sheets, email_sender

# ------------------------------------------------------------------
# 🔧 Environment setup
# ------------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"), override=True)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ------------------------------------------------------------------
# 🌍 Multilingual Natural Message
# ------------------------------------------------------------------
def build_multilingual_message(intent: str, hotel_name: str) -> str:
    """Return a polite bilingual (English + Amharic) hospitality message."""
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")

    greetings_en = [
        f"🛎️ Dear guest, thank you for choosing *{hotel_name}*!",
        f"Welcome to *{hotel_name}*, we’re delighted to assist you!",
        f"Your booking request at *{hotel_name}* has been received."
    ]
    followup_en = [
        "Our front desk team will confirm your stay shortly.",
        "You’ll receive your confirmation soon.",
        "We’re reviewing availability and will update you soon."
    ]

    greetings_am = [
        f"🛎️ እንኳን ወደ *{hotel_name}* በደህና መጡ።",
        f"ውድ እንግዳ፣ ስለ *{hotel_name}* መያዣዎ እናመሰግናለን።",
        f"የ *{hotel_name}* መያዣዎ ተቀብያለች።"
    ]
    followup_am = [
        "በቅርቡ ይረጋገጣል።",
        "የፊት ገቢ ቡድናችን በቅርቡ ይዘጋጅልዎታል።",
        "በቅርቡ መያዣዎን እናረጋግጣለን።"
    ]

    eng = f"{random.choice(greetings_en)}\n{random.choice(followup_en)}\n📅 {today}"
    amh = f"{random.choice(greetings_am)} {random.choice(followup_am)}"

    return f"{eng}\n\n{amh}\n\n— *Guzo Guest Assist Front Desk*"


# ------------------------------------------------------------------
# 🎯 Intent Detection
# ------------------------------------------------------------------
def detect_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["book", "reserve", "stay", "room", "night", "መያዣ", "ሆቴል"]):
        return "booking"
    if any(w in msg for w in ["cancel", "change", "modify", "delete", "መሰረዝ", "መቀየር"]):
        return "cancellation"
    if any(w in msg for w in ["hi", "hello", "price", "available", "ሰላም", "ዋጋ"]):
        return "inquiry"
    return "general"


# ------------------------------------------------------------------
# 📨 Telegram Sender
# ------------------------------------------------------------------
async def send_telegram_message(chat_id: str, text: str):
    """Send Telegram message to hotel contact."""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        print(f"📱 Telegram sent → {chat_id}")
        return True
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return False


# ------------------------------------------------------------------
# 🤖 Main Confirmation Handler
# ------------------------------------------------------------------
async def confirm_guest_request(guest_name, hotel_name, message, recipient_email=None):
    """Send confirmation via Email + Telegram and log results."""
    intent = detect_intent(message)
    print(f"📨 Processing {intent} for {guest_name} ({hotel_name})")

    record = google_sheets.find_hotel_record(hotel_name)
    if not record:
        print(f"[WARN] No hotel record found for {hotel_name}.")
        return "Hotel Not Found"

    # 1️⃣ Email
    email_status = "Not Sent"
    recipient = recipient_email or record.get("Reservation Email") or record.get("Main Contact Email")
    if recipient:
        try:
            subject = f"Guzo Guest Assist – {intent.title()} Confirmation"
            body = build_multilingual_message(intent, hotel_name)
            sent = email_sender.send_email(recipient, subject, body)
            email_status = "Email Sent" if sent else "Email Failed"
            print(f"[EmailSender] {email_status} → {recipient}")
        except Exception as e:
            print(f"⚠️ Email failed: {e}")
            email_status = "Email Failed"

    # 2️⃣ Telegram
    tg_status = "Not Sent"
    chat_id = record.get("Telegram Chat ID") or record.get("Chat ID")
    if chat_id:
        try:
            msg = build_multilingual_message(intent, hotel_name)
            tg_success = await send_telegram_message(str(chat_id).strip(), msg)
            tg_status = "Telegram Sent" if tg_success else "Telegram Failed"
        except Exception as e:
            print(f"⚠️ Telegram send error: {e}")
            tg_status = "Telegram Failed"

    # 3️⃣ Unified Google Sheets Logging
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            guest_name,
            "Telegram",
            "",
            "",
            "",
            "",
            "",
            "",
            email_status,
            "",
            "Unpaid",
            "",
            "",
            "System",
            "Auto via Guzo Bot",
            f"{intent.title()} confirmation via auto_confirmation.py"
        ]
        google_sheets.log_booking_to_sheets(hotel_name, row)
        print(f"🗂️ Logged confirmation for {guest_name} ({hotel_name}) → {email_status}, {tg_status}")
    except Exception as e:
        print(f"⚠️ Logging to Google Sheets failed: {e}")

    return f"{email_status}, {tg_status}"
