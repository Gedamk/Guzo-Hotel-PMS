# -*- coding: utf-8 -*-
"""
conversational_booking_v2.py
----------------------------------------------------
AI-powered front-desk assistant for Guzo Guest Assist.
Handles bilingual (English + Amharic) guest conversations,
hotel self-registration, booking confirmations, and payment.
"""

import os
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
from guzo_booking_bot.modules.email_sender import send_email
from guzo_booking_bot.modules.google_sheets import (
    log_booking,
    find_hotel_record,
    load_hotel_contacts,
)
from guzo_booking_bot.modules.auto_register import (
    register_hotel,
    handle_test_booking_callback,
)

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

ASK_HOTEL, HOTEL_CONFIRM, ASK_GUESTS, ASK_DATES, ASK_ROOM, ASK_GUEST_INFO, CONFIRM = range(7)
reply_keyboard_rooms = [["Standard", "Deluxe", "Suite"]]

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the guest in English + Amharic."""
    welcome_text = (
        "í¼ Welcome to **Guzo Guest Assist**, your digital hospitality desk.\n\n"
        "I can help you book rooms across our partner hotels.\n"
        "You can type something like:\n"
        "â¢ âBook a room at Sky Light Hotel for 2 guests.â\n"
        "â¢ âWeâll arrive this weekend and stay 2 nights.â\n\n"
        "á¥áá³á áá° áá ááµáµ á áµáµáµ á á°áá áá¡á¢"
    )
    await update.message.reply_text(welcome_text)
    return ASK_HOTEL


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def ask_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1 â Capture hotel name and check availability."""
    user_text = update.message.text.strip()
    context.user_data["hotel_query"] = user_text
    hotel_info = find_hotel_record(user_text)

    # Suggest correction if fuzzy match found
    if hotel_info and "suggested_name" in hotel_info:
        context.user_data["suggested_hotel"] = hotel_info["suggested_name"]
        await update.message.reply_text(
            f"í´ I couldnât find **{user_text}**, did you mean **{hotel_info['suggested_name']}**?"
        )
        return HOTEL_CONFIRM

    # No hotel match found
    if not hotel_info:
        hotels = load_hotel_contacts() or []
        available = [h["Hotel Name"] for h in hotels if h.get("Availability", "").lower() in ["yes", "available"]]
        alt_text = "\nâ¢ ".join(available[:3]) if available else "No available hotels at the moment."
        await update.message.reply_text(
            f"â ï¸ Sorry, **{user_text}** is not found in our partner list.\n\n"
            f"Here are a few available hotels you can choose:\nâ¢ {alt_text}\n\n"
            "Please type the hotel name you'd like to book."
        )
        return ASK_HOTEL

    # Check availability
    if hotel_info.get("Availability", "").lower() not in ["yes", "available"]:
        hotels = load_hotel_contacts() or []
        city = hotel_info.get("City", "")
        alternatives = [
            h["Hotel Name"] for h in hotels
            if h.get("Availability", "").lower() in ["yes", "available"]
            and h.get("City", "") == city
        ]
        alt_text = "\nâ¢ ".join(alternatives[:3]) if alternatives else "No available hotels in this city."
        await update.message.reply_text(
            f"â ï¸ {hotel_info['Hotel Name']} is currently unavailable.\n\n"
            f"Here are some nearby options in {city}:\nâ¢ {alt_text}\n\n"
            "Please type your preferred hotel."
        )
        return ASK_HOTEL

    # Valid hotel found
    context.user_data["hotel"] = hotel_info.get("Hotel Name")
    context.user_data["hotel_info"] = hotel_info
    await update.message.reply_text("â¨ Great choice! How many guests will be staying?")
    return ASK_GUESTS


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def confirm_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm hotel suggestion."""
    reply = update.message.text.strip().lower()
    suggested = context.user_data.get("suggested_hotel")

    if reply in ["yes", "y", "ok", "confirm", "sure"]:
        context.user_data["hotel"] = suggested
        await update.message.reply_text(
            f"â Excellent! Booking will continue with **{suggested}**.\nHow many guests will be staying?"
        )
        return ASK_GUESTS
    else:
        await update.message.reply_text("Alright, please type the correct hotel name again.")
        return ASK_HOTEL


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def ask_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2 â Guest count."""
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text(
        "í³ When will you be checking in, and for how many nights?\nExample: October 25 to 27"
    )
    return ASK_DATES


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def ask_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3 â Dates."""
    context.user_data["dates"] = update.message.text.strip()
    await update.message.reply_text(
        "í»ï¸ What room type would you prefer?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_rooms, one_time_keyboard=True)
    )
    return ASK_ROOM


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def ask_guest_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4 â Collect guest info (name, email, phone)."""
    context.user_data["room"] = update.message.text.strip()
    await update.message.reply_text(
        "í±¤ May I have your full name, email, and phone number?\n"
        "Example:\nJohn Doe | johndoe@email.com | +251911223344"
    )
    return ASK_GUEST_INFO


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 5 â Confirm details."""
    info_text = update.message.text.strip()
    parts = [p.strip() for p in info_text.split("|")]
    context.user_data["guest_name"] = parts[0] if len(parts) > 0 else "Guest"
    context.user_data["guest_email"] = parts[1] if len(parts) > 1 else ""
    context.user_data["guest_phone"] = parts[2] if len(parts) > 2 else ""

    info = context.user_data
    summary = (
        f"í¿¨ Hotel: {info['hotel']}\n"
        f"í±¥ Guests: {info['guests']}\n"
        f"í³ Dates: {info['dates']}\n"
        f"í»ï¸ Room Type: {info['room']}\n"
        f"í¹ Guest: {info['guest_name']}\n"
        f"í³§ Email: {info['guest_email']}\n"
        f"í³± Phone: {info['guest_phone']}\n\n"
        "Please confirm these details before proceeding."
    )

    await update.message.reply_text(
        f"{summary}\nType **Yes** to confirm or **No** to make changes.\n"
        "á¥á£á­á á­áá áá«á£ á«á¨ááá¡á¢"
    )
    return CONFIRM


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 6 â Confirm, email, log, and show payment link."""
    if update.message.text.strip().lower() not in ["yes", "y", "confirm"]:
        await update.message.reply_text("â Booking cancelled. You can start again anytime.")
        return ConversationHandler.END

    info = context.user_data
    hotel_info = info.get("hotel_info", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confirmation_id = f"{info['hotel'][:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    manager_email = hotel_info.get("Manager Email") or os.getenv("DEFAULT_MANAGER_EMAIL", "owner@guzoassist.com")
    payment_link = hotel_info.get("Payment Link") or "https://pay.guzoassist.com"

    subject = f"New Booking â {info['hotel']}"
    body = (
        f"<b>í³© New Guest Booking via Guzo Guest Assist</b><br><br>"
        f"í¿¨ <b>Hotel:</b> {info['hotel']}<br>"
        f"í±¥ <b>Guests:</b> {info['guests']}<br>"
        f"í³ <b>Dates:</b> {info['dates']}<br>"
        f"í»ï¸ <b>Room:</b> {info['room']}<br>"
        f"í¹ <b>Name:</b> {info['guest_name']}<br>"
        f"í³§ <b>Email:</b> {info['guest_email']}<br>"
        f"í³± <b>Phone:</b> {info['guest_phone']}<br>"
        f"íµ <b>Time:</b> {timestamp}<br>"
        f"í´¢ <b>Confirmation ID:</b> {confirmation_id}<br><br>"
        f"í²³ <b>Payment:</b> <a href='{payment_link}'>Pay Securely Online</a><br><br>"
        f"<i>This message was generated automatically by Guzo Guest Assist.</i>"
    )

    try:
        send_email(manager_email, subject, body)
        print(f"â Email sent to {manager_email}")
    except Exception as e:
        print("â ï¸ Email sending failed:", e)

    try:
        log_booking(
            hotel=info["hotel"],
            guests=info["guests"],
            dates=info["dates"],
            room=info["room"],
            guest_name=info["guest_name"],
            timestamp=timestamp,
        )
    except Exception as e:
        print("â ï¸ Google Sheets logging error:", e)

    pay_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("í²³ Pay Online", url=payment_link)]]
    )
    await update.message.reply_text(
        f"â Your booking has been confirmed!\n\n"
        f"í³ Confirmation ID: {confirmation_id}\n"
        f"í³§ Email sent to: {manager_email}\n\n"
        f"í²³ You can complete your payment online below:",
        reply_markup=pay_button,
    )
    return ConversationHandler.END


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel process."""
    await update.message.reply_text(
        "â Booking cancelled. Say 'Book a room' to start again anytime."
    )
    return ConversationHandler.END


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def main():
    """Main entry â Telegram bot launcher."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("â TELEGRAM_BOT_TOKEN not found in .env.")
        return

    app = ApplicationBuilder().token(token).build()

    # â Add registration + test callback
    app.add_handler(CommandHandler("register", register_hotel))
    app.add_handler(CallbackQueryHandler(handle_test_booking_callback))

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("(?i)book|room|stay|reservation"), ask_hotel)],
        states={
            ASK_HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_hotel)],
            HOTEL_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_hotel)],
            ASK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_dates)],
            ASK_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_room)],
            ASK_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_guest_info)],
            ASK_GUEST_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize)],
        },
        fallbacks=[MessageHandler(filters.Regex("(?i)cancel|stop|exit"), cancel)],
    )

    app.add_handler(MessageHandler(filters.Regex("(?i)hi|hello|hey|good|morning|evening"), greet))
    app.add_handler(conv)

    print("í´ Guzo Hospitality Assistant running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
