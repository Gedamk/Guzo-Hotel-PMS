# -*- coding: utf-8 -*-
"""
booking_flow.py – Guzo Guest Assist Conversational Booking Flow (v6.3)
----------------------------------------------------------------------
Triggered automatically when user mentions booking.
Fills all 17 hotel columns, logs into Google Sheets, and
sends hospitality-standard confirmation emails.

✅ v6.3 updates:
- Capture Property Code from Hotel_Contacts_Master
- Generate Confirmation ID
- Push booking into Central_Bookings + Postgres via central_sync
"""

import os
import datetime
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from guzo_backend.modules import google_sheets, email_sender
from guzo_backend.modules.central_sync import sync_booking_to_central

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

logger = logging.getLogger(__name__)

# Session memory per Telegram user
sessions = {}


# =====================================================================
# 🧠 Conversational Booking Flow
# =====================================================================
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
                "🛎️ Please type the hotel name exactly as registered "
                "(e.g., Sofi Hotel, Aron Luxury Hotel)."
            )
            return

        # Save hotel info into session
        data["Hotel Name"] = rec.get("Hotel Name") or rec.get("name") or text
        data["Property Code"] = (
            rec.get("Property Code")
            or rec.get("property_code")
            or rec.get("Code")
        )
        data["Hotel Record"] = rec  # keep whole record for later (email, etc.)

        session["step"] = "checkin"
        sessions[uid] = session

        await update.message.reply_text(
            f"✅ Great! Booking at *{data['Hotel Name']}*.\n"
            f"Please enter Check-In Date (YYYY-MM-DD).",
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
            await update.message.reply_text(
                "Please enter Check-Out Date (YYYY-MM-DD)."
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ Invalid format. Please type date as YYYY-MM-DD."
            )
        sessions[uid] = session
        return

    # ------------------------------------------------------------
    # 🗓️ Step 3: Check-Out
    # ------------------------------------------------------------
    if session["step"] == "checkout":
        try:
            co = datetime.datetime.strptime(text, "%Y-%m-%d").date()
            ci = datetime.datetime.strptime(
                data["Check-In Date"], "%Y-%m-%d"
            ).date()
            nights = (co - ci).days
            if nights <= 0:
                await update.message.reply_text(
                    "⚠️ Check-Out must be after Check-In. Try again."
                )
                return
            data["Check-Out Date"] = str(co)
            data["Nights"] = nights
            session["step"] = "room"
            await update.message.reply_text(
                f"✅ {nights} night(s). Please enter Room Type (e.g., Deluxe)."
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ Invalid date. Use YYYY-MM-DD."
            )
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
            sessions[uid] = session

            kb = [["Cash", "Card", "Bank Transfer"]]
            await update.message.reply_text(
                f"💵 Total Revenue: *{data['Total Revenue (ETB)']:,.2f} ETB*.\n"
                f"Select Payment Method:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    kb, one_time_keyboard=True, resize_keyboard=True
                ),
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ Please enter a valid amount (e.g., 2500)."
            )
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
            f"🏨 *{data.get('Hotel Name', 'Unknown Hotel')}*\n"
            f"👤 Guest: {guest_name}\n"
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
    # ✅ Step 7: Confirm and Log (Sheets + Central + Postgres)
    # ------------------------------------------------------------
    if session["step"] == "confirm":
        if text.lower() != "yes":
            await update.message.reply_text(
                "❌ Booking cancelled.", reply_markup=ReplyKeyboardRemove()
            )
            sessions.pop(uid, None)
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate a confirmation ID (simple timestamp-based)
        confirmation_id = "GUZO-" + datetime.datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )
        data["Confirmation ID"] = confirmation_id

        # Build proper 17-column booking row for per-hotel sheet
        # Columns:
        # [Timestamp, Guest Name, Source, Check-In Date, Check-Out Date,
        #  Nights, Room Type, Rate Per Night (ETB), Total Revenue (ETB),
        #  Booking Status, Confirmation ID, Payment Status, Payment Date,
        #  Payment Method, Handled By, Auto Reply, Remark]
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
            "Confirmed",           # Booking Status
            confirmation_id,       # Confirmation ID
            "Unpaid",              # Payment Status (can be updated later)
            "",                    # Payment Date
            data["Payment Method"],
            "System",
            "Auto via Guzo Bot",
            "Confirmed via guest dialogue",
        ]

        hotel_name = data.get("Hotel Name", "Unknown Hotel")
        property_code = data.get("Property Code")
        hotel_record = data.get("Hotel Record", {}) or {}

        # ✅ Log booking into per-hotel sheet
        google_sheets.log_booking_to_sheets(hotel_name, row)

        # ✅ Prepare canonical booking for central_sync → Central_Bookings + Postgres
        central_booking = {
            "Hotel Name": hotel_name,
            "Guest Name": guest_name,
            "Source": "Telegram",
            "Check-In Date": data["Check-In Date"],
            "Check-Out Date": data["Check-Out Date"],
            "Nights": data["Nights"],
            "Room Type": data["Room Type"],
            "Rate Per Night (ETB)": data["Rate Per Night (ETB)"],
            "Total Revenue (ETB)": data["Total Revenue (ETB)"],
            "Booking Status": "Confirmed",
            "Payment Status": "Unpaid",
            "Payment Method": data["Payment Method"],
            "Confirmation ID": confirmation_id,
            # Extra fields used by postgres_bookings
            "property_code": property_code,
            "guest_email": None,  # You can collect this in future steps
        }

        try:
            logger.info(
                "[BookingFlow] Sending booking to central_sync "
                "(hotel=%s, confirmation_id=%s, property_code=%s)",
                hotel_name,
                confirmation_id,
                property_code,
            )
            sync_ok = sync_booking_to_central(central_booking)
            if not sync_ok:
                logger.warning(
                    "[BookingFlow] central_sync returned False for confirmation_id=%s",
                    confirmation_id,
                )
        except Exception as e:
            logger.exception(
                "[BookingFlow] Error calling central_sync for confirmation_id=%s: %s",
                confirmation_id,
                e,
            )

        # ✅ Send email confirmation to hotel contact (as before)
        recipient = (
            hotel_record.get("Main Contact Email")
            or hotel_record.get("Reservation Email")
            or hotel_record.get("Hotel Email")
        )

        if recipient:
            body = (
                f"Dear {guest_name},\n\n"
                f"Your reservation at {hotel_name} is confirmed.\n\n"
                f"Confirmation ID: {confirmation_id}\n\n"
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
            try:
                email_sender.send_email(
                    recipient,
                    f"Booking Confirmation – {hotel_name} ({confirmation_id})",
                    body,
                )
            except Exception as e:
                logger.exception(
                    "[BookingFlow] Failed to send confirmation email "
                    "for confirmation_id=%s: %s",
                    confirmation_id,
                    e,
                )

        # ✅ Final guest-facing message
        await update.message.reply_text(
            f"✅ Dear {guest_name}, your booking at *{hotel_name}* is confirmed!\n"
            f"🔐 Confirmation ID: `{confirmation_id}`\n"
            f"📅 {data['Check-In Date']} → {data['Check-Out Date']}\n"
            f"🌙 Nights: {data['Nights']} | 🛏️ {data['Room Type']} | "
            f"💳 {data['Payment Method']}\n"
            "We look forward to welcoming you.\n\n— Guzo Guest Assist",
            parse_mode="Markdown",
        )

        sessions.pop(uid, None)
        return
