# -*- coding: utf-8 -*-
"""
conversational_booking.py – Guzo Guest Assist (v5.5 Smart Trigger Edition)
---------------------------------------------------------------------------
Natural-language booking assistant that detects intent from normal text
("hi", "book room", "need reservation") and launches the interactive
hotel booking flow with Google Sheets integration.
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)
from datetime import datetime
from guzo_booking_bot.modules.log_helper import log_event

# --- Booking States ---
HOTEL, GUESTS, NIGHTS, BREAKFAST, NOTES, CONFIRM = range(6)

# --- Google Sheets Integration ---
def save_booking_to_sheet(booking_data):
    """Save confirmed booking details to Google Sheets."""
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_booking_bot/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
        sheet = client.open_by_key(SHEET_ID).worksheet("Bookings")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([
            now,
            booking_data.get("hotel", ""),
            booking_data.get("guests", ""),
            booking_data.get("nights", ""),
            booking_data.get("breakfast", ""),
            booking_data.get("notes", ""),
            booking_data.get("guest_name", ""),
            booking_data.get("chat_id", "")
        ])
        print(f"✅ Booking saved: {booking_data.get('hotel')}")
        log_event("Booking", "SAVED",
                  f"Booking logged for {booking_data.get('hotel')}")
    except Exception as e:
        print(f"⚠️ Google Sheets error: {e}")
        log_event("Booking", "ERROR", f"Save failed: {e}")

# --- Start booking conversation ---
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "Guest"
    hotels = ["Guzo-Booking Assist", "Sky Light Test", "Central Test Hotel"]
    keyboard = [[h] for h in hotels]

    await update.message.reply_text(
        f"👋 Hello {user}! Welcome to *Guzo Guest Assist*.\n\n"
        "I can help you make a quick hotel reservation.\n"
        "Please select which hotel you’d like to stay at:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    log_event("Conversation", "START", f"{user} began a booking session.")
    return HOTEL

# --- Step 1: Hotel ---
async def hotel_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text.strip()
    await update.message.reply_text("🏷 How many guests will be staying?",
                                    reply_markup=ReplyKeyboardRemove())
    return GUESTS

# --- Step 2: Guests ---
async def guests_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text("🛏 For how many nights will you stay?")
    return NIGHTS

# --- Step 3: Nights ---
async def nights_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nights"] = update.message.text.strip()
    keyboard = [["🍳 Bed & Breakfast", "🚪 Room Only"]]
    await update.message.reply_text(
        "Would you like breakfast included?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return BREAKFAST

# --- Step 4: Breakfast ---
async def breakfast_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["breakfast"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 Any special requests or notes for your stay?\n(Type 'No' if none.)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NOTES

# --- Step 5: Notes ---
async def notes_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notes"] = update.message.text.strip()
    summary = (
        "📋 *Booking Summary*\n"
        "----------------------------------\n"
        f"🏨 Hotel: {context.user_data['hotel']}\n"
        f"👥 Guests: {context.user_data['guests']}\n"
        f"🛏 Nights: {context.user_data['nights']}\n"
        f"🍽 Plan: {context.user_data['breakfast']}\n"
        f"🗒 Notes: {context.user_data['notes']}\n\n"
        "Please confirm your reservation below 👇"
    )
    keyboard = [["✅ Confirm Booking", "❌ Cancel"]]
    await update.message.reply_text(
        summary, parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CONFIRM

# --- Step 6: Confirm ---
async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "Guest"
    chat_id = update.effective_chat.id
    booking_data = {
        "hotel": context.user_data.get("hotel"),
        "guests": context.user_data.get("guests"),
        "nights": context.user_data.get("nights"),
        "breakfast": context.user_data.get("breakfast"),
        "notes": context.user_data.get("notes"),
        "guest_name": user,
        "chat_id": chat_id,
    }
    save_booking_to_sheet(booking_data)
    await update.message.reply_text(
        "🎉 Thank you! Your booking has been recorded.\n"
        "Our hotel team will confirm your stay shortly.\n\n"
        "🌍 We appreciate your trust in *Guzo Guest Assist!*",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
    )
    log_event("Booking", "CONFIRMED",
              f"{user} confirmed booking for {booking_data['hotel']}")
    return ConversationHandler.END

# --- Cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "Guest"
    await update.message.reply_text(
        "❌ Booking cancelled. You can start again anytime by typing 'book room'.",
        reply_markup=ReplyKeyboardRemove(),
    )
    log_event("Booking", "CANCELLED", f"{user} cancelled.")
    return ConversationHandler.END

# --- Smart Trigger Detector ---
TRIGGER_WORDS = [
    "book", "booking", "reserve", "reservation",
    "room", "stay", "night", "hi", "hello", "hey"
]

async def detect_booking_intent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start booking if message contains a trigger word."""
    text = (update.message.text or "").lower()
    if any(word in text for word in TRIGGER_WORDS):
        return await start_booking(update, context)
    else:
        await update.message.reply_text(
            "👋 Hi! I can help you book a room. Try typing 'book room' to begin."
        )

# --- Conversation Handler Factory ---
def create_booking_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("book", start_booking),
            MessageHandler(filters.TEXT & ~filters.COMMAND, detect_booking_intent)
        ],
        states={
            HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, hotel_chosen)],
            GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, guests_chosen)],
            NIGHTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, nights_chosen)],
            BREAKFAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, breakfast_chosen)],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, notes_received)],
            CONFIRM: [
                MessageHandler(filters.Regex("^(✅|confirm|yes)$"), confirm_booking),
                MessageHandler(filters.Regex("^(❌|cancel|no)$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
