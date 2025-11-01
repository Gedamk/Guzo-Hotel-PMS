# -*- coding: utf-8 -*-
"""
message_router.py â Guzo Guest Assist Smart Router (v10)
--------------------------------------------------------
Routes Telegram messages to the right service:
 - Detects booking/cancellation intent
 - Logs guest requests to Google Sheets
 - Sends Telegram + Email confirmation automatically
"""

from telegram import Update
from telegram.ext import ContextTypes
from guzo_booking_bot.modules import google_sheets
from guzo_booking_bot.modules.auto_confirmation import confirm_guest_request
from guzo_booking_bot.modules.reply_flow import detect_language, classify_message


# ======================================================
# MAIN MESSAGE HANDLER
# ======================================================
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main router for incoming Telegram messages."""
    message = update.message.text.strip()
    user = update.message.from_user
    guest_name = user.first_name or "Guest"
    print(f"í³© Message received from {guest_name}: {message}")

    # Detect message type
    intent = classify_message(message)
    language = detect_language(message)

    # Extract hotel name (basic keyword search)
    hotel_name = "Sky Light Hotel"  # Default fallback
    if "sky" in message.lower():
        hotel_name = "Sky Light Hotel"
    elif "sofi" in message.lower():
        hotel_name = "Sofi Hotel"
    elif "haile" in message.lower():
        hotel_name = "Haile Resort"
    elif "lewi" in message.lower():
        hotel_name = "Lewi Resort"

    # Log request to Google Sheets
    google_sheets.init_client()
    google_sheets.log_new_request(
        guest_name=guest_name,
        hotel_name=hotel_name,
        message=message,
        status="Pending"
    )

    # Dummy recipient email (you can load dynamically later)
    recipient_email = "manager@skylighthotel.com"

    # Trigger auto confirmation (Telegram + Email)
    await confirm_guest_request(
        update=update,
        context=context,
        guest_name=guest_name,
        hotel_name=hotel_name,
        message=message,
        recipient_email=recipient_email
    )

    print(f"â Confirmation completed for {guest_name} ({hotel_name})")
