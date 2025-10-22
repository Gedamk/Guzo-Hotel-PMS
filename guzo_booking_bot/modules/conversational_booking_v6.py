# -*- coding: utf-8 -*-
"""
conversational_booking_v6.py â€“ Guzo Guest Assist (Multilingual Concierge)
--------------------------------------------------------------------------
Handles smart conversational bookings with automatic language detection,
multi-hotel sheet logging, and standard hospitality dialogue in Amharic + English.
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)
from datetime import datetime
from guzo_booking_bot.modules.log_helper import log_event

# --- Booking Steps ---
LANG, HOTEL, ROOMTYPE, GUESTS, NIGHTS, BREAKFAST, ARRIVAL, PICKUP, NOTES, CONFIRM = range(10)

# --- Language Strings ---
TEXT = {
    "en": {
        "welcome": "í±‹ Hello! Welcome to *Guzo Guest Assist*.\nI can help you book a hotel room.\nPlease select your language:",
        "choose_hotel": "Please choose the hotel you'd like to stay at:",
        "room_type": "What room type would you prefer?",
        "guests": "How many guests will be staying?",
        "nights": "For how many nights will you stay?",
        "breakfast": "Would you like breakfast included?",
        "arrival": "What time will you arrive?",
        "pickup": "Would you like an airport pickup?",
        "notes": "Any special requests or notes?",
        "summary_title": "í³‹ *Booking Summary*",
        "confirm": "Please confirm your reservation below í±‡",
        "thank_you": "í¾‰ Thank you! Your booking has been recorded.\nOur hotel team will confirm your stay shortly.\ní¼� We appreciate your trust in *Guzo Guest Assist!*",
        "cancel": "â�Œ Booking cancelled. You can start again anytime.",
        "yes": "Yes",
        "no": "No",
    },
    "am": {
        "welcome": "í±‹ áŠ¥áŠ•áŠ³áŠ• á‹ˆá‹° *áŒ‰á‹ž áŒˆáˆµá‰µ áŠ áˆ²áˆµá‰µ* á‰ á‹°áˆ…áŠ“ áˆ˜áŒ¡á�¢\náŠ­á��áˆ� áˆˆáˆ˜á‹«á‹� áŠ¥á‰½áˆ‹áˆˆáˆ�á�¢\náŠ¥á‰£áŠ­á‹Ž á‰‹áŠ•á‰‹ á‹­áˆ�áˆ¨áŒ¡á�¢",
        "choose_hotel": "áŠ¥á‰£áŠ­á‹Ž áˆˆáˆ˜á‰€áˆ˜áŒ¥ á‹¨áˆšá�ˆáˆ�áŒ‰á‰µáŠ• áˆ†á‰´áˆ� á‹­áˆ�áˆ¨áŒ¡á�¢",
        "room_type": "á‹¨áŠ­á��áˆ� áŠ á‹­áŠ�á‰µ á‹­áˆ�áˆ¨áŒ¡á�¢",
        "guests": "áˆµáŠ•á‰µ áŠ¥áŠ•áŒ�á‹¶á‰½ á‹­á‰†á‹«áˆ‰?",
        "nights": "áˆµáŠ•á‰µ áˆŒáˆŠá‰¶á‰½ á‹­á‰†á‹«áˆ‰?",
        "breakfast": "á‰�áˆ­áˆµ áŠ¥áŠ•á‹²áŠ«á‰°á‰µ á‰µá�ˆáˆ�áŒ‹áˆˆáˆ…?",
        "arrival": "á‰ áˆ�áŠ• áˆ°á‹“á‰µ á‰µá‹°áˆ­áˆ³áˆˆáˆ…?",
        "pickup": "áŠ¨áŠ á‹¨áˆ­ áˆ˜áŠ•áŒˆá‹µ áˆ˜á‹�áˆ°á‹µ á‰µá�ˆáˆ�áŒ‹áˆˆáˆ…?",
        "notes": "áˆŒáˆ‹ áˆ�á‹© á��áˆ‹áŒŽá‰µ á‹ˆá‹­áˆ� áŠ áˆµá‰°á‹«á‹¨á‰µ?",
        "summary_title": "í³‹ *á‹¨á‰†á‹­á‰³ áˆ›áŒ á‰ƒáˆˆá‹«*",
        "confirm": "áŠ¥á‰£áŠ­á‹Ž á‰µáŠ­áŠ­áˆˆáŠ› áˆ˜áˆ†áŠ‘áŠ• á‹«áˆ¨áŒ‹áŒ�áŒ¡ í±‡",
        "thank_you": "í¾‰ áŠ¥áŠ“áˆ˜áˆ°áŒ�áŠ“áˆˆáŠ•! á‹¨á‰†á‹­á‰³á‹Ž áˆ˜áˆ¨áŒƒ á‰°áˆ˜á‹�áŒ�á‰§áˆ�á�¢\ná‹¨áˆ†á‰´áˆ‰ á‰¡á‹µáŠ• á‰ á‰…áˆ­á‰¡ á‹«áˆ¨áŒ‹áŒ�áŒ£áˆ�á�¢\ní¼� áŠ¥áŠ“áˆ˜áˆ°áŒ�áŠ“áˆˆáŠ•á�¢",
        "cancel": "â�Œ á‰†á‹­á‰³ á‰°áˆ°áˆ­á‹Ÿáˆ�á�¢ á‰ áˆ›áŠ•áŠ›á‹�áˆ� áŒŠá‹œ áˆ˜áŒ€áˆ˜áˆ­ á‰µá‰½áˆ‹áˆˆáˆ…á�¢",
        "yes": "áŠ á‹Ž",
        "no": "áŠ á‹­á‹°áˆˆáˆ�",
    }
}

# --- Sheets Save ---
def save_booking_to_sheet(booking_data):
    """Save confirmed booking details to Google Sheets (auto hotel tab)."""
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
        hotel_name = booking_data.get("hotel", "Bookings")
        try:
            sheet = client.open_by_key(SHEET_ID).worksheet(hotel_name)
        except:
            sheet = client.open_by_key(SHEET_ID).add_worksheet(title=hotel_name, rows="100", cols="10")
            sheet.append_row([
                "Timestamp", "Hotel", "Guest Name", "Room Type", "Guests",
                "Nights", "Breakfast", "Arrival", "Pickup", "Notes", "Chat ID"
            ])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([
            now,
            booking_data.get("hotel", ""),
            booking_data.get("guest_name", ""),
            booking_data.get("room_type", ""),
            booking_data.get("guests", ""),
            booking_data.get("nights", ""),
            booking_data.get("breakfast", ""),
            booking_data.get("arrival", ""),
            booking_data.get("pickup", ""),
            booking_data.get("notes", ""),
            booking_data.get("chat_id", "")
        ])
        print(f"âœ… Booking saved to {hotel_name} tab.")
        log_event("Booking", "SAVED", f"{hotel_name} booking saved.")
    except Exception as e:
        print(f"âš ï¸� Google Sheets error: {e}")
        log_event("Booking", "ERROR", str(e))

# --- Conversation Flow ---
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["í·¬í·§ English", "í·ªí·¹ áŠ áˆ›áˆ­áŠ›"]]
    await update.message.reply_text(
        TEXT["en"]["welcome"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "áŠ áˆ›áˆ­" in text or "í·ªí·¹" in text:
        context.user_data["lang"] = "am"
    else:
        context.user_data["lang"] = "en"
    lang = context.user_data["lang"]

    hotels = ["Guzo-Booking Assist", "Sky Light Test", "Central Test Hotel"]
    keyboard = [[h] for h in hotels]
    await update.message.reply_text(TEXT[lang]["choose_hotel"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return HOTEL

async def hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["hotel"] = update.message.text.strip()
    keyboard = [["Single", "Double", "Suite"]]
    await update.message.reply_text(TEXT[lang]["room_type"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return ROOMTYPE

async def roomtype(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["room_type"] = update.message.text.strip()
    await update.message.reply_text(TEXT[lang]["guests"], reply_markup=ReplyKeyboardRemove())
    return GUESTS

async def guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text(TEXT[lang]["nights"])
    return NIGHTS

async def nights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["nights"] = update.message.text.strip()
    keyboard = [[TEXT[lang]["yes"], TEXT[lang]["no"]]]
    await update.message.reply_text(TEXT[lang]["breakfast"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return BREAKFAST

async def breakfast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["breakfast"] = update.message.text.strip()
    await update.message.reply_text(TEXT[lang]["arrival"], reply_markup=ReplyKeyboardRemove())
    return ARRIVAL

async def arrival(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["arrival"] = update.message.text.strip()
    keyboard = [[TEXT[lang]["yes"], TEXT[lang]["no"]]]
    await update.message.reply_text(TEXT[lang]["pickup"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return PICKUP

async def pickup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["pickup"] = update.message.text.strip()
    await update.message.reply_text(TEXT[lang]["notes"], reply_markup=ReplyKeyboardRemove())
    return NOTES

async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["notes"] = update.message.text.strip()
    summary = (
        f"{TEXT[lang]['summary_title']}\n"
        f"í¿¨ {context.user_data['hotel']}\n"
        f"í¿  {context.user_data['room_type']}\n"
        f"í±¥ {context.user_data['guests']} guests\n"
        f"í»� {context.user_data['nights']} nights\n"
        f"í½³ {context.user_data['breakfast']}\n"
        f"íµ“ Arrival: {context.user_data['arrival']}\n"
        f"íº— Pickup: {context.user_data['pickup']}\n"
        f"í·’ Notes: {context.user_data['notes']}"
    )
    keyboard = [["âœ… Confirm", "â�Œ Cancel"]]
    await update.message.reply_text(summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown")
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    user = update.effective_user.first_name or "Guest"
    chat_id = update.effective_chat.id
    context.user_data["guest_name"] = user
    context.user_data["chat_id"] = chat_id
    save_booking_to_sheet(context.user_data)
    await update.message.reply_text(TEXT[lang]["thank_you"], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(TEXT[lang]["cancel"], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Conversation Handler Factory ---
def create_booking_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, start_booking)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, hotel)],
            ROOMTYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, roomtype)],
            GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, guests)],
            NIGHTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, nights)],
            BREAKFAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, breakfast)],
            ARRIVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, arrival)],
            PICKUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, pickup)],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, notes)],
            CONFIRM: [
                MessageHandler(filters.Regex("^(âœ…|Confirm|confirm)$"), confirm),
                MessageHandler(filters.Regex("^(â�Œ|Cancel|cancel)$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
