# -*- coding: utf-8 -*-
"""
booking_handler.py – Guzo Guest Assist Telegram Booking Flow
-------------------------------------------------------------
Lets guests make reservations via Telegram.
Logs data into Google Sheets using google_sheets.py.
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from guzo_booking_bot.modules.google_sheets import log_booking

# ───────────────────────────────────────────────
# Conversation States
# ───────────────────────────────────────────────
ASK_HOTEL, ASK_GUESTS, ASK_DATE, ASK_ROOM, ASK_NAME = range(5)

# ───────────────────────────────────────────────
# Logger Setup
# ───────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ───────────────────────────────────────────────
# Conversation Handlers
# ───────────────────────────────────────────────
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏨 Which hotel would you like to book?")
    return ASK_HOTEL


async def ask_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hotel"] = update.message.text.strip()
    await update.message.reply_text("👥 How many guests?")
    return ASK_GUESTS


async def ask_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text("📅 What are the check-in and check-out dates? (e.g., Oct 25–27)")
    return ASK_DATE


async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dates"] = update.message.text.strip()
    await update.message.reply_text("🛏️ What room type would you like?")
    return ASK_ROOM


async def ask_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text.strip()
    await update.message.reply_text("👤 Guest name?")
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guest_name"] = update.message.text.strip()

    hotel = context.user_data["hotel"]
    guests = context.user_data["guests"]
    dates = context.user_data["dates"]
    room = context.user_data["room"]
    guest_name = context.user_data["guest_name"]

    await update.message.reply_text("🔄 Saving your booking, please wait...")

    try:
        success = log_booking(
            hotel=hotel,
            guests=guests,
            dates=dates,
            room=room,
            guest_name=guest_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if success:
            await update.message.reply_text(
                f"✅ Booking confirmed for *{guest_name}* at *{hotel}*!\n"
                f"🗓️ {dates} | 👥 {guests} guest(s) | 🛏️ {room}\n\n"
                "We'll notify you once the hotel confirms. 💬",
                parse_mode="Markdown",
            )
            logger.info(f"Booking saved for {guest_name} ({hotel})")
        else:
            await update.message.reply_text("⚠️ Booking could not be saved. Please try again later.")
    except Exception as e:
        logger.error(f"Booking error: {e}", exc_info=True)
        await update.message.reply_text("❌ Error occurred while saving booking.")
    finally:
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Booking cancelled.")
    return ConversationHandler.END


def get_booking_conversation_handler():
    """Return a ConversationHandler configured for /book command."""
    return ConversationHandler(
        entry_points=[CommandHandler("book", start_booking)],
        states={
            ASK_HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_hotel)],
            ASK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_guests)],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
            ASK_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_room)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
