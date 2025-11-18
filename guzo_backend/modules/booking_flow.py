# -*- coding: utf-8 -*-
"""
booking_flow.py – Guzo Guest Assist Conversational Booking Flow (v6.2)
---------------------------------------------------------------------
Triggered automatically when user mentions booking.
Fills all 17 hotel columns, logs into Google Sheets, and
sends hospitality-standard confirmation emails.
"""

import os
import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from guzo_backend.modules import google_sheets, email_sender

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Session memory per Telegram user
sessions = {}


# ================================================================
# 🧠 Conversational Booking Flow
# ================================================================
async def handle_booking_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    text = update.message.text.strip()
    guest_name = user.full_name or "Guest"

    session = sessions.get(uid, {"step": "detect", "data": {"Guest Name": guest_name}})
    data = session["data"]

    # ------------------------------------------------------------
    # 🏨 Step 1: Detect hotel
    # ------------------------------------------------------------
    if session["step"] == "detect":
        rec = google_sheets.find_hotel_record(text)
        if not rec:
            await update.message.reply_text(
                "🛎️ Please type the hotel name exactly as registered (e.g., Sofi Hotel, Aron Luxury Hotel)."
            )
            return
        data["Hotel Name"] = rec["Hotel Name"]
        session["step"] = "checkin"
        sessions[uid] = session
        await update.message.reply_text(
            f"✅ Great! Booking at *{data['Hotel Name']}*.\nPlease enter Check-In Date (YYYY-MM-DD).",
            parse_mode="Markdown",
        )
        return

    # ------------------------------------------------------------
    # 🗓️ Step 2: Check-In
    # ------------------------------------------------------------
    if session["step"] == "checkin":
        try:
            ci = datetime.datetime.strptime(text, "%Y-%m-%d").date()
            data["Check-In Date"] = str(ci)
            session["step"] = "checkout"
            await update.message.reply_text("Please enter Check-Out Date (YYYY-MM-DD).")
        except Exception:
            await update.message.reply_text("⚠️ Invalid format. Please type date as YYYY-MM-DD.")
        sessions[uid] = session
        return

    # ------------------------------------------------------------
    # 🗓️ Step 3: Check-Out
    # ------------------------------------------------------------
    if session["step"] == "checkout":
        try:
            co = datetime.datetime.strptime(text, "%Y-%m-%d").date()
            ci = datetime.datetime.strptime(data["Check-In Date"], "%Y-%m-%d").date()
            nights = (co - ci).days
            if nights <= 0:
                await update.message.reply_text("⚠️ Check-Out must be after Check-In. Try again.")
                return
            data["Check-Out Date"] = str(co)
            data["Nights"] = nights
            session["step"] = "room"
            await update.message.reply_text(f"✅ {nights} night(s). Please enter Room Type (e.g., Deluxe).")
        except Exception:
            await update.message.reply_text("⚠️ Invalid date. Use YYYY-MM-DD.")
        sessions[uid] = session
        return

    # ------------------------------------------------------------
    # 🛏️ Step 4: Room Type
    # ------------------------------------------------------------
    if session["step"] == "room":
        data["Room Type"] = text
        session["step"] = "rate"
        sessions[uid] = session
        await update.message.reply_text("Please enter Rate Per Night (ETB).")
        return

    # ------------------------------------------------------------
    # 💵 Step 5: Rate
    # ------------------------------------------------------------
    if session["step"] == "rate":
        try:
            rate = float(text)
            data["Rate Per Night (ETB)"] = rate
            data["Total Revenue (ETB)"] = rate * data["Nights"]
            session["step"] = "payment"
            kb = [["Cash", "Card", "Bank Transfer"]]
            await update.message.reply_text(
                f"💵 Total Revenue: *{data['Total Revenue (ETB)']:,.2f} ETB*.\nSelect Payment Method:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True),
            )
        except Exception:
            await update.message.reply_text("⚠️ Please enter a valid amount (e.g., 2500).")
        sessions[uid] = session
        return

    # ------------------------------------------------------------
    # 💳 Step 6: Payment Method
    # ------------------------------------------------------------
    if session["step"] == "payment":
        data["Payment Method"] = text
        session["step"] = "confirm"
        sessions[uid] = session
        await update.message.reply_text(
            f"Please confirm your booking:\n"
            f"🏨 *{data['Hotel Name']}*\n"
            f"📅 Check-In: {data['Check-In Date']}\n"
            f"📅 Check-Out: {data['Check-Out Date']}\n"
            f"🌙 Nights: {data['Nights']}\n"
            f"🛏️ Room Type: {data['Room Type']}\n"
            f"💰 Rate/Night: {data['Rate Per Night (ETB)']:,.2f} ETB\n"
            f"💳 Payment: {data['Payment Method']}\n\n"
            "Type *yes* to confirm or *no* to cancel.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # ------------------------------------------------------------
    # ✅ Step 7: Confirm and Log
    # ------------------------------------------------------------
    if session["step"] == "confirm":
        if text.lower() != "yes":
            await update.message.reply_text("❌ Booking cancelled.", reply_markup=ReplyKeyboardRemove())
            sessions.pop(uid, None)
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build proper 17-column booking row
        row = [
            timestamp,
            guest_name,
            "Telegram",
            data["Check-In Date"],
            data["Check-Out Date"],
            data["Nights"],
            data["Room Type"],
            data["Rate Per Night (ETB)"],
            data["Total Revenue (ETB)"],
            "Confirmed",
            "",
            "Unpaid",
            "",
            data["Payment Method"],
            "System",
            "Auto via Guzo Bot",
            "Confirmed via guest dialogue",
        ]

        # ✅ Log booking into both sheets
        google_sheets.log_booking_to_sheets(data["Hotel Name"], row)

        # ✅ Send email confirmation
        rec = google_sheets.find_hotel_record(data["Hotel Name"])
        if rec:
            recipient = rec.get("Main Contact Email") or rec.get("Reservation Email")
            if recipient:
                body = (
                    f"Dear {guest_name},\n\n"
                    f"Your reservation at {data['Hotel Name']} is confirmed.\n\n"
                    f"Check-In: {data['Check-In Date']}\n"
                    f"Check-Out: {data['Check-Out Date']}\n"
                    f"Nights: {data['Nights']}\n"
                    f"Room Type: {data['Room Type']}\n"
                    f"Rate: {data['Rate Per Night (ETB)']:,} ETB per night\n"
                    f"Total: {data['Total Revenue (ETB)']:,} ETB\n"
                    f"Payment Method: {data['Payment Method']}\n\n"
                    "We look forward to welcoming you soon.\n\n"
                    "— Guzo Guest Assist Front Desk"
                )
                email_sender.send_email(
                    recipient,
                    f"Booking Confirmation – {data['Hotel Name']}",
                    body,
                )

        await update.message.reply_text(
            f"✅ Dear {guest_name}, your booking at *{data['Hotel Name']}* is confirmed!\n"
            f"📅 {data['Check-In Date']} → {data['Check-Out Date']}\n"
            f"🌙 Nights: {data['Nights']} | 🛏️ {data['Room Type']} | 💳 {data['Payment Method']}\n"
            "We look forward to welcoming you.\n\n— Guzo Guest Assist",
            parse_mode="Markdown",
        )

        sessions.pop(uid, None)
        return
