# -*- coding: utf-8 -*-
"""
conversational_booking_v2.py
----------------------------------------------------
AI-powered multilingual front-desk assistant for Guzo Guest Assist 🌍🇪🇹
Handles English + Amharic guest conversations, self-registration,
booking confirmations, and secure online payments via Chapa.
"""

import os
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv
from guzo_booking_bot.modules.email_sender import send_email
from guzo_booking_bot.modules.google_sheets import (
    log_booking, find_hotel_record, load_hotel_contacts
)
from guzo_booking_bot.modules.auto_register import register_hotel
from guzo_booking_bot.modules.payment_gateway import generate_chapa_link

# ──────────────────────────────────────────────────────────────
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

ASK_HOTEL, HOTEL_CONFIRM, ASK_GUESTS, ASK_DATES, ASK_ROOM, ASK_GUEST_INFO, CONFIRM = range(7)
reply_keyboard_rooms = [["Standard", "Deluxe", "Suite"]]

# ──────────────────────────────────────────────────────────────
async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warm bilingual greeting for guests."""
    text = (
        "🌞 Welcome to **Guzo Guest Assist** — your 24/7 digital hospitality desk.\n\n"
        "I can help you book rooms across our partner hotels.\n"
        "You can type something like:\n"
        "• 'Book a room at Sky Light Hotel for 2 guests'\n"
        "• 'We’ll arrive this weekend and stay 2 nights'\n\n"
        "እንኳን ወደ ጉዞ ጌስት አስስት በደህና መጡ። "
        "የሚፈልጉትን ሆቴል እና ቀናት ይጻፉ።"
    )
    await update.message.reply_text(text)
    return ASK_HOTEL

# ──────────────────────────────────────────────────────────────
async def ask_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1 — Identify hotel from user text."""
    query = update.message.text.strip()
    context.user_data["hotel_query"] = query
    hotel_info = find_hotel_record(query)

    if hotel_info and "suggested_name" in hotel_info:
        context.user_data["suggested_hotel"] = hotel_info["suggested_name"]
        await update.message.reply_text(
            f"🤔 I couldn’t find **{query}**, did you mean **{hotel_info['suggested_name']}**?"
        )
        return HOTEL_CONFIRM

    if not hotel_info:
        hotels = load_hotel_contacts() or []
        suggestions = [h["Hotel Name"] for h in hotels[:3]]
        msg = "\n• ".join(suggestions) if suggestions else "No partners available."
        await update.message.reply_text(
            f"⚠️ Sorry, **{query}** isn’t in our partner list.\n\n"
            f"Here are some you can choose:\n• {msg}\n\n"
            "Please type the hotel name you'd like to book."
        )
        return ASK_HOTEL

    context.user_data["hotel"] = hotel_info["Hotel Name"]
    context.user_data["hotel_info"] = hotel_info
    await update.message.reply_text("✨ Great choice! How many guests will be staying?")
    return ASK_GUESTS

# ──────────────────────────────────────────────────────────────
async def confirm_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.text.strip().lower()
    suggestion = context.user_data.get("suggested_hotel")
    if reply in ["yes", "y", "ok", "confirm"]:
        context.user_data["hotel"] = suggestion
        await update.message.reply_text(
            f"✅ Excellent! Continuing with **{suggestion}**.\nHow many guests will be staying?"
        )
        return ASK_GUESTS
    else:
        await update.message.reply_text("Alright, please type the correct hotel name again.")
        return ASK_HOTEL

# ──────────────────────────────────────────────────────────────
async def ask_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text("📅 When will you be checking in, and for how many nights?")
    return ASK_DATES

# ──────────────────────────────────────────────────────────────
async def ask_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dates"] = update.message.text.strip()
    await update.message.reply_text(
        "🛏️ What room type would you prefer?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_rooms, one_time_keyboard=True)
    )
    return ASK_ROOM

# ──────────────────────────────────────────────────────────────
async def ask_guest_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text.strip()
    await update.message.reply_text(
        "👤 Please provide your full name, email, and phone number.\n\n"
        "Example:\nJohn Doe | john@example.com | +251911223344\n\n"
        "እባክዎ ስምዎን፣ ኢሜይልዎን፣ ስልክ ቁጥርዎን ያስገቡ።"
    )
    return ASK_GUEST_INFO

# ──────────────────────────────────────────────────────────────
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = update.message.text.strip()
    parts = [p.strip() for p in info_text.split("|")]
    context.user_data["guest_name"] = parts[0] if len(parts) > 0 else "Guest"
    context.user_data["guest_email"] = parts[1] if len(parts) > 1 else ""
    context.user_data["guest_phone"] = parts[2] if len(parts) > 2 else ""

    i = context.user_data
    summary = (
        f"🏨 Hotel: {i['hotel']}\n"
        f"👥 Guests: {i['guests']}\n"
        f"📅 Dates: {i['dates']}\n"
        f"🛏️ Room: {i['room']}\n"
        f"🙍 Guest: {i['guest_name']}\n"
        f"📧 Email: {i['guest_email']}\n"
        f"📱 Phone: {i['guest_phone']}\n\n"
        "Please confirm these details.\nእባክዎ ይህን መያዣ ያረጋግጡ።"
    )
    await update.message.reply_text(summary + "\n\nType **Yes** to confirm or **No** to change.")
    return CONFIRM

# ──────────────────────────────────────────────────────────────
async def finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 6 — Confirm booking, log, email, and send Chapa payment link."""
    if update.message.text.strip().lower() not in ["yes", "y", "confirm"]:
        await update.message.reply_text("❌ Booking cancelled. You can start again anytime.")
        return ConversationHandler.END

    i = context.user_data
    h = i.get("hotel_info", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confirmation_id = f"{i['hotel'][:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    manager_email = h.get("Manager Email") or os.getenv("DEFAULT_MANAGER_EMAIL", "owner@guzoassist.com")
    currency = h.get("Currency", "ETB")

    # 💰 Generate payment link using Chapa
    try:
        payment_link = generate_chapa_link(
            booking_id=confirmation_id,
            amount=1000.00,  # TODO: compute dynamically
            currency=currency,
            guest_email=i["guest_email"]
        )
    except Exception as e:
        payment_link = None
        print("⚠️ Payment link error:", e)

    # 📨 Compose bilingual email
    subject = f"New Booking – {i['hotel']}"
    body = f"""
    <h3>📩 New Guest Booking via Guzo Guest Assist</h3>
    <p><b>Hotel:</b> {i['hotel']}<br>
    <b>Guests:</b> {i['guests']}<br>
    <b>Dates:</b> {i['dates']}<br>
    <b>Room:</b> {i['room']}<br>
    <b>Name:</b> {i['guest_name']}<br>
    <b>Email:</b> {i['guest_email']}<br>
    <b>Phone:</b> {i['guest_phone']}<br>
    <b>Time:</b> {timestamp}<br>
    <b>Confirmation ID:</b> {confirmation_id}</p>
    <hr>
    <p><b>Payment Link / የክፍያ መንገድ:</b> 
    <a href="{payment_link or 'https://pay.guzoassist.com'}">Pay Now / አሁን ይክፈሉ</a></p>
    """

    try:
        send_email(manager_email, subject, body)
        print(f"✅ Email sent to {manager_email}")
    except Exception as e:
        print("⚠️ Email send failed:", e)

    try:
        log_booking(
            hotel=i["hotel"], guests=i["guests"], dates=i["dates"],
            room=i["room"], guest_name=i["guest_name"], timestamp=timestamp
        )
    except Exception as e:
        print("⚠️ Sheets logging failed:", e)

    # 💬 Telegram confirmation bilingual
    buttons = [[InlineKeyboardButton("💳 Pay Online / አሁን ይክፈሉ", url=payment_link or "https://pay.guzoassist.com")]]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"✅ Your booking has been confirmed!\n\n"
        f"📄 Confirmation ID: {confirmation_id}\n"
        f"📧 Email sent to: {manager_email}\n\n"
        f"💳 Click below to complete payment securely.\n\n"
        f"እባክዎ መያዣው ተሳክቷል። እንኳን በደህና መጡ።",
        reply_markup=markup
    )
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Booking cancelled. Say 'Book a room' to start again.")
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN missing.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("register", register_hotel))

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

    app.add_handler(MessageHandler(filters.Regex("(?i)hi|hello|hey|selam|good"), greet))
    app.add_handler(conv)

    print("🤖 Guzo Hospitality Assistant running... Press Ctrl + C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()



