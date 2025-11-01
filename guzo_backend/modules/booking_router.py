# -*- coding: utf-8 -*-
"""
booking_router.py – Smart Booking Router for Guzo Guest Assist
----------------------------------------------------------------
Routes guest booking messages to the correct hotel manager
using Telegram Chat IDs from the Google Sheet registry.
"""

import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ContextTypes
from guzo_backend.modules.log_helper import log_event
from difflib import get_close_matches

# ✅ Google Sheet Info
SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
TAB_NAME = "Hotels"


def clean_name(name: str):
    """Normalize hotel names for comparison."""
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"(hotel|resort|inn|guest\s*house)", "", name)
    name = re.sub(r"[^a-z0-9\s]", "", name)
    return name.strip()


def get_hotel_contact(hotel_name: str):
    """Looks up Telegram Chat ID for the hotel manager."""
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_backend/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(TAB_NAME)
        rows = sheet.get_all_records()

        hotel_names = [r.get("Hotel Name", "").strip() for r in rows if r.get("Hotel Name")]
        print("🟢 Available hotels:", hotel_names)

        cleaned_hotels = {clean_name(h): h for h in hotel_names}
        cleaned_input = clean_name(hotel_name)

        best_match = get_close_matches(cleaned_input, cleaned_hotels.keys(), n=1, cutoff=0.3)
        if not best_match:
            print(f"❌ No close match for '{hotel_name}'")
            return None, None

        match_clean = best_match[0]
        match_name = cleaned_hotels[match_clean]
        print(f"✅ Matched '{hotel_name}' → '{match_name}'")

        for row in rows:
            if row["Hotel Name"].strip().lower() == match_name.lower():
                return match_name, row.get("Telegram Chat ID")

        return match_name, None
    except Exception as e:
        log_event("BookingRouter", "ERROR", f"Error fetching hotel contact: {e}")
        print(f"❌ Error fetching hotel contact: {e}")
        return None, None


# ✅ Telegram command handler
async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /book <hotel_name> <booking_message>
    Example:
    /book Sky Light Hotel Test 2 adults arriving Friday
    """
    try:
        if not context.args:
            await update.message.reply_text("Usage: /book <hotel_name> <booking details>")
            return

        full_text = " ".join(context.args)
        print(f"🟢 Guest message: {full_text}")

        # ✅ Extract likely hotel name (first 3–4 words)
        possible_name = " ".join(full_text.split()[:4])
        print(f"🔍 Trying to match possible hotel name: '{possible_name}'")

        matched_hotel, manager_chat_id = get_hotel_contact(possible_name)

        if not matched_hotel:
            msg = "❌ Sorry, I couldn’t find any hotel matching your request."
            await update.message.reply_text(msg)
            log_event("BookingRouter", "NOT_FOUND", msg)
            print(f"❌ No match found for text: {full_text}")
            return

        if not manager_chat_id:
            msg = f"⚠️ No Telegram Chat ID found for {matched_hotel}."
            await update.message.reply_text(msg)
            log_event("BookingRouter", "MISSING_CHAT_ID", msg)
            return

        # Extract the booking message (text after hotel name)
        split_index = full_text.lower().find(matched_hotel.lower())
        booking_message = full_text[split_index + len(matched_hotel):].strip() if split_index >= 0 else full_text
        if not booking_message:
            booking_message = "(no message provided)"

        guest_name = update.effective_user.first_name or "Guest"
        log_event("BookingRouter", "BOOKING_SENT", f"{guest_name} → {matched_hotel}")

        await context.bot.send_message(
            chat_id=manager_chat_id,
            text=(
                f"📩 *New Booking Request* from {guest_name}\n\n"
                f"🏨 Hotel: {matched_hotel}\n"
                f"💬 Message: {booking_message}\n\n"
                f"Reply here to respond to the guest."
            ),
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            f"✅ Your booking request has been sent to {matched_hotel}!"
        )

        print(f"📤 Forwarded booking from {guest_name} to {matched_hotel} ({manager_chat_id})")

    except Exception as e:
        log_event("BookingRouter", "ERROR", f"Unhandled error: {e}")
        await update.message.reply_text("⚠️ An error occurred while processing your booking.")
        print(f"❌ BookingRouter error: {e}")
