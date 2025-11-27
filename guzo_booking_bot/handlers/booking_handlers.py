# guzo_booking_bot/handlers/booking_handlers.py
#
# Conversation flow for:
#   1) Select hotel (property_code)
#   2) Enter check-in / check-out dates
#   3) Check availability via backend /bot/availability  <-- #3
#   4) If available, collect guest info
#   5) Create booking via backend /bot/bookings
#
# This file is designed for python-telegram-bot (v13 style).
# You still need to wire the handlers into your main_telegram_bot.py.

import os
import requests
from typing import Tuple

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
)

# --------------------------------------------------------------------
# Config
# --------------------------------------------------------------------

GUZO_API_BASE = os.getenv("GUZO_API_BASE", "http://127.0.0.1:8000")

# Hotel mapping (you can extend this later)
PROPERTY_CHOICES = {
    "Dream Big Hotel": "DRE001",
    "N&N Luxury Hotel": "N&N002",
}

PROPERTY_KEYBOARD = [
    ["Dream Big Hotel", "N&N Luxury Hotel"],
]

# Conversation states
(
    CHOOSING_PROPERTY,
    ASK_CHECK_IN,
    ASK_CHECK_OUT,
    CHECK_AVAILABILITY,
    ASK_GUEST_NAME,
    ASK_GUEST_PHONE,
    CONFIRM_BOOKING,
) = range(7)


# --------------------------------------------------------------------
# Backend helpers
# --------------------------------------------------------------------

def call_bot_availability(
    property_code: str,
    check_in: str,
    check_out: str,
    rooms: int = 1,
) -> dict:
    """
    Calls your backend:
      GET /bot/availability?hotel=...&in=...&out=...&rooms=...
    Returns parsed JSON dict.
    """
    url = f"{GUZO_API_BASE}/bot/availability"
    params = {
        "hotel": property_code,
        "in": check_in,
        "out": check_out,
        "rooms": rooms,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def call_bot_create_booking(
    property_code: str,
    check_in: str,
    check_out: str,
    guest_name: str,
    guest_phone: str,
    rooms: int = 1,
    language: str = "en",
    channel: str = "telegram",
) -> dict:
    """
    Calls your backend:
      POST /bot/bookings
    Body must match your FastAPI BotBookingCreate model.
    Adjust field names if your backend is slightly different.
    """
    url = f"{GUZO_API_BASE}/bot/bookings"
    payload = {
        "property_code": property_code,
        "check_in": check_in,
        "check_out": check_out,
        "rooms": rooms,
        "guest_name": guest_name,
        "guest_phone": guest_phone,
        "language": language,
        "channel": channel,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------
# Conversation handlers
# --------------------------------------------------------------------

def start_booking(update: Update, context: CallbackContext) -> int:
    """
    Entry point for booking conversation.
    """
    chat_id = update.effective_chat.id
    context.user_data.clear()

    update.message.reply_text(
        "Welcome to Guzo Guest Assist 🛎\n\n"
        "Which hotel would you like to book?",
        reply_markup=ReplyKeyboardMarkup(
            PROPERTY_KEYBOARD,
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return CHOOSING_PROPERTY


def handle_property_choice(update: Update, context: CallbackContext) -> int:
    """
    User chooses the hotel (human name). We map it to property_code.
    """
    chat_id = update.effective_chat.id
    choice = (update.message.text or "").strip()

    property_code = PROPERTY_CHOICES.get(choice)
    if not property_code:
        update.message.reply_text(
            "Sorry, I didn’t recognize that hotel. Please choose from the buttons."
        )
        return CHOOSING_PROPERTY

    context.user_data["hotel_name"] = choice
    context.user_data["property_code"] = property_code

    update.message.reply_text(
        f"Great! You selected {choice}.\n\n"
        "Please send your check-in date in the format YYYY-MM-DD (for example: 2025-12-01).",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_CHECK_IN


def handle_check_in(update: Update, context: CallbackContext) -> int:
    """
    Save check-in date as plain string. You can add validation later.
    """
    check_in = (update.message.text or "").strip()
    context.user_data["check_in"] = check_in

    update.message.reply_text(
        "Got it ✅\nNow send your check-out date in the format YYYY-MM-DD "
        "(for example: 2025-12-03)."
    )

    return ASK_CHECK_OUT


def handle_check_out(update: Update, context: CallbackContext) -> int:
    """
    Save check-out date and move to availability check (#3).
    """
    check_out = (update.message.text or "").strip()
    context.user_data["check_out"] = check_out

    # Immediately go to availability check
    return check_availability_step(update, context)


def check_availability_step(update: Update, context: CallbackContext) -> int:
    """
    This is the #3 step: call backend /bot/availability
    after we have property_code, check_in, check_out.
    """
    chat_id = update.effective_chat.id

    property_code = context.user_data.get("property_code")
    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")

    if not property_code or not check_in or not check_out:
        update.message.reply_text(
            "Missing information to check availability. Let’s start again."
        )
        return start_booking(update, context)

    try:
        result = call_bot_availability(
            property_code=property_code,
            check_in=check_in,
            check_out=check_out,
            rooms=1,
        )

        # Show backend message directly (it’s already human-readable).
        update.message.reply_text(result.get("message", "Availability checked."))

        if result.get("available"):
            update.message.reply_text(
                "Perfect! 🎉\nRooms are available.\n\n"
                "Please send the guest full name."
            )
            return ASK_GUEST_NAME
        else:
            update.message.reply_text(
                "Unfortunately there is no availability for these dates.\n"
                "You can try different dates or another hotel."
            )
            # You can either go back to dates or property choice. For now: dates again.
            update.message.reply_text(
                "Send a new check-in date (YYYY-MM-DD) to try again."
            )
            return ASK_CHECK_IN

    except Exception as e:
        print("Error while calling /bot/availability:", e)
        update.message.reply_text(
            "Sorry, I couldn’t check availability right now. Please try again."
        )
        return ASK_CHECK_IN


def handle_guest_name(update: Update, context: CallbackContext) -> int:
    """
    Store guest's full name.
    """
    guest_name = (update.message.text or "").strip()
    context.user_data["guest_name"] = guest_name

    update.message.reply_text(
        "Thanks 🙏\nNow please send the guest phone number (with country code if possible)."
    )
    return ASK_GUEST_PHONE


def handle_guest_phone(update: Update, context: CallbackContext) -> int:
    """
    Store guest phone and then confirm booking.
    """
    guest_phone = (update.message.text or "").strip()
    context.user_data["guest_phone"] = guest_phone

    hotel_name = context.user_data.get("hotel_name")
    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")
    guest_name = context.user_data.get("guest_name")

    summary = (
        f"Please confirm your booking details:\n\n"
        f"🏨 Hotel: {hotel_name}\n"
        f"📅 Check-in: {check_in}\n"
        f"📅 Check-out: {check_out}\n"
        f"👤 Guest: {guest_name}\n"
        f"📞 Phone: {guest_phone}\n\n"
        "Send 'Yes' to confirm or 'No' to cancel."
    )

    update.message.reply_text(summary)
    return CONFIRM_BOOKING


def handle_confirm_booking(update: Update, context: CallbackContext) -> int:
    """
    If user confirms, call backend /bot/bookings.
    """
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip().lower()

    if text not in ("yes", "y", "አዎ", "aye"):
        update.message.reply_text("Booking cancelled. If you wish, you can start again.")
        return ConversationHandler.END

    property_code = context.user_data.get("property_code")
    check_in = context.user_data.get("check_in")
    check_out = context.user_data.get("check_out")
    guest_name = context.user_data.get("guest_name")
    guest_phone = context.user_data.get("guest_phone")

    try:
        result = call_bot_create_booking(
            property_code=property_code,
            check_in=check_in,
            check_out=check_out,
            guest_name=guest_name,
            guest_phone=guest_phone,
            rooms=1,
            language="en",
            channel="telegram",
        )

        booking_code = result.get("booking_code", "N/A")
        update.message.reply_text(
            f"✅ Your booking is confirmed!\n\n"
            f"Booking code: {booking_code}\n"
            f"Hotel: {context.user_data.get('hotel_name')}\n"
            f"Check-in: {check_in}\n"
            f"Check-out: {check_out}\n\n"
            f"Thank you for booking with Guzo Guest Assist 🛎"
        )
    except Exception as e:
        print("Error while calling /bot/bookings:", e)
        update.message.reply_text(
            "Sorry, I could not complete your booking. Please try again later."
        )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """
    Standard cancel handler.
    """
    update.message.reply_text("Booking cancelled. See you next time 👋")
    return ConversationHandler.END


# --------------------------------------------------------------------
# Helper: build ConversationHandler
# --------------------------------------------------------------------

def build_booking_conversation_handler(entry_command: str = "book") -> ConversationHandler:
    """
    Returns a ConversationHandler that you can add to your Dispatcher in main_telegram_bot.py:

        from guzo_booking_bot.handlers.booking_handlers import build_booking_conversation_handler
        updater.dispatcher.add_handler(build_booking_conversation_handler("book"))

    Then, in Telegram, user types /book to start.
    """
    from telegram.ext import CommandHandler, MessageHandler, Filters

    return ConversationHandler(
        entry_points=[CommandHandler(entry_command, start_booking)],
        states={
            CHOOSING_PROPERTY: [
                MessageHandler(Filters.text & ~Filters.command, handle_property_choice)
            ],
            ASK_CHECK_IN: [
                MessageHandler(Filters.text & ~Filters.command, handle_check_in)
            ],
            ASK_CHECK_OUT: [
                MessageHandler(Filters.text & ~Filters.command, handle_check_out)
            ],
            ASK_GUEST_NAME: [
                MessageHandler(Filters.text & ~Filters.command, handle_guest_name)
            ],
            ASK_GUEST_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, handle_guest_phone)
            ],
            CONFIRM_BOOKING: [
                MessageHandler(Filters.text & ~Filters.command, handle_confirm_booking)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="booking_conversation",
        persistent=False,
    )
