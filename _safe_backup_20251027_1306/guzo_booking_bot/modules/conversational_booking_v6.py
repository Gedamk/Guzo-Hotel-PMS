# -*- coding: utf-8 -*-
"""
conversational_booking_v2.py
----------------------------------------------------
Bilingual (English + Amharic) conversational booking assistant
for Guzo Guest Assist – high-standard global hospitality front desk simulation.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

from guzo_booking_bot.modules.email_sender import send_email as send_confirmation_email
from guzo_booking_bot.modules.google_sheets import init_client, log_booking_to_sheet

# Load environment variables
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

# Conversation states
ASK_HOTEL, ASK_GUESTS, ASK_DATES, ASK_ROOM, CONFIRM = range(5)

# Sample hotel data for follow-up
HOTEL_CONTACTS = {
    "Sofi Hotel": {
        "phone": "+251 911 123 456",
        "email": "info@sofihotel.com",
        "telegram": "https://t.me/sofihotel"
    },
    "Sky Light Hotel": {
        "phone": "+251 912 222 333",
        "email": "info@skylighthotel.com",
        "telegram": "https://t.me/skylighthotel"
    },
    "Haile Resort": {
        "phone": "+251 930 987 654",
        "email": "info@hailereso.com",
        "telegram": "https://t.me/hailereso"
    }
}

reply_keyboard_hotels = [["Sofi Hotel", "Sky Light Hotel", "Haile Resort"]]
reply_keyboard_rooms = [["Standard", "Deluxe", "Suite"]]


# --- Language Detector ---
def detect_language(text: str) -> str:
    for ch in text:
        if "\u1200" <= ch <= "\u137F":
            return "am"
    return "en"


# --- Step 1: Start Booking ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.first_name or "Guest"
    text = update.message.text or ""
    lang = detect_language(text)

    if lang == "am":
        welcome_text = (
            f"ሰላም {user}! እንኳን ወደ ጉዞ ጌስት አሲስት በደህና መጡ።\n\n"
            f"እባኮትን የሚመዝገቡትን ሆቴል ይምረጡ።"
        )
    else:
        welcome_text = (
            f"🤖 Hello {user}!\n"
            f"Welcome to Guzo Guest Assist.\n\n"
            f"Please choose the hotel you’d like to book:"
        )

    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_hotels, one_time_keyboard=True)
    )
    return ASK_HOTEL


# --- Step 2: Ask for Guests ---
async def ask_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text
    lang = detect_language(update.message.text)

    question = (
        "ለትንሹ ግለሰቦች ወይም እንግዶች ቁጥር ይጻፉ።"
        if lang == "am"
        else "How many guests will stay?"
    )
    await update.message.reply_text(question)
    return ASK_GUESTS


# --- Step 3: Ask for Dates ---
async def ask_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guests"] = update.message.text
    lang = detect_language(update.message.text)

    question = (
        "እባኮትን የመግቢያ እና የመውጫ ቀን ይጻፉ (ለምሳሌ፦ ነሐሴ 5 - 7)"
        if lang == "am"
        else "Please enter your check-in and check-out dates (e.g., Oct 25–27)."
    )
    await update.message.reply_text(question)
    return ASK_DATES


# --- Step 4: Ask for Room Type ---
async def ask_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dates"] = update.message.text
    lang = detect_language(update.message.text)

    question = (
        "እባኮትን የክፍል አይነት ይምረጡ።"
        if lang == "am"
        else "Please select your room type:"
    )

    await update.message.reply_text(
        question,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_rooms, one_time_keyboard=True)
    )
    return ASK_ROOM


# --- Step 5: Confirm Booking ---
async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room_type"] = update.message.text
    data = context.user_data
    hotel = data["hotel"]
    guests = data["guests"]
    dates = data["dates"]
    room = data["room_type"]

    confirmation = (
        f"✅ የተመዘገበው ጥያቄ እንደሚከተለው ነው፦\n\n"
        f"🏨 ሆቴል፦ {hotel}\n"
        f"👥 እንግዶች፦ {guests}\n"
        f"📅 ቀናት፦ {dates}\n"
        f"🛏️ ክፍል፦ {room}\n\n"
        f"እባክዎን ያረጋግጡ (አዎ / አይደለም)"
        if detect_language(update.message.text) == "am"
        else f"✅ Booking Summary\n\n🏨 Hotel: {hotel}\n👥 Guests: {guests}\n📅 Dates: {dates}\n🛏️ Room Type: {room}\n\nPlease confirm (Yes / No)."
    )

    await update.message.reply_text(confirmation)
    return CONFIRM


# --- Step 6: Finalize Booking and Send Follow-Up ---
async def finalize_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    lang = detect_language(text)
    data = context.user_data
    hotel = data.get("hotel")
    guests = data.get("guests")
    dates = data.get("dates")
    room = data.get("room_type")

    if text in ["yes", "አዎ", "አዎን"]:
        # Send email confirmation
        manager_email = f"manager@{hotel.replace(' ', '').lower()}.com"
        subject = f"New Booking - {hotel}"
        body = f"Booking confirmed:\nHotel: {hotel}\nGuests: {guests}\nDates: {dates}\nRoom: {room}"
        send_confirmation_email(manager_email, subject, body)

        # Log to Google Sheets
        try:
            init_client()
            log_booking_to_sheet(hotel, guests, dates, room)
        except Exception as e:
            print(f"⚠️ Google Sheets log failed: {e}")

        # Send thank-you follow-up with contact info
        contact = HOTEL_CONTACTS.get(hotel, {})
        phone = contact.get("phone", "N/A")
        email = contact.get("email", "N/A")
        tg = contact.get("telegram", "N/A")

        if lang == "am":
            message = (
                f"✅ ትዕዛዙ ተሳክቷል። እናመሰግናለን።\n\n"
                f"📞 የሆቴሉ ስልክ፦ {phone}\n"
                f"📧 ኢሜይል፦ {email}\n"
                f"🔗 ቴሌግራም፦ {tg}\n\n"
                f"ጉዞ ጌስት አሲስት ከተመረጡት ለመግቢያ እና አገልግሎት እንመሰግናለን።"
            )
        else:
            message = (
                f"✅ Booking confirmed successfully!\n\n"
                f"📞 Contact: {phone}\n"
                f"📧 Email: {email}\n"
                f"🔗 Telegram: {tg}\n\n"
                f"Thank you for choosing Guzo Guest Assist — we look forward to welcoming you soon!"
            )

        await update.message.reply_text(message)

    else:
        cancel_text = (
            "🚫 ትዕዛዙ ተሰረዘ።" if lang == "am" else "🚫 Booking cancelled."
        )
        await update.message.reply_text(cancel_text)

    return ConversationHandler.END


# --- Cancel Handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update.message.text)
    msg = (
        "ትዕዛዙ ተሰረዘ። እናመሰግናለን።"
        if lang == "am"
        else "Booking cancelled. Thank you."
    )
    await update.message.reply_text(msg)
    return ConversationHandler.END


# --- Conversation Handler ---
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("book", start),
        MessageHandler(filters.Regex("(?i)book|reserve|hotel|room|booking|reservation|stay"), start),
        MessageHandler(filters.Regex("(መዝገብ|ክፍል|ሆቴል|ቦታ|ቆይታ|ማረፊያ)"), start),
    ],
    states={
        ASK_HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_guests)],
        ASK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_dates)],
        ASK_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_room)],
        ASK_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_booking)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_booking)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# --- Run the Bot ---
if __name__ == "__main__":
    print("🤖 Conversational booking assistant running...")
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(conv_handler)
    app.run_polling()
