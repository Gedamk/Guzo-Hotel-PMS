# -*- coding: utf-8 -*-
"""
auto_register.py
----------------------------------------------------
Automatically registers hotels when they run /register <Hotel Name>
and saves their Telegram Chat ID directly into Google Sheets.

After registration, sends a welcome setup card
with hotel info, Guzo Guest Assist logo emoji, and a test booking button.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from guzo_backend.modules.google_sheets import (
    init_client,
    get_hotel_contact_sheet_id,
)

# ──────────────────────────────────────────────────────────────
# Load environment variables
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)


# ──────────────────────────────────────────────────────────────
def add_hotel_chat_id(hotel_name: str, chat_id: int):
    """
    Register or update a hotel's Telegram Chat ID in Hotel_Contacts_Master.
    - If the hotel exists → updates its Telegram Chat ID
    - If the hotel doesn’t exist → adds a new row automatically
    Returns (status, hotel_data)
    """
    try:
        sheet_id = get_hotel_contact_sheet_id()
        if not sheet_id:
            print("⚠️ No Hotel Contacts Master Sheet ID found in .env file.")
            return False, None

        client = init_client()
        if not client:
            print("⚠️ Google Sheets client unavailable.")
            return False, None

        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_records()
        headers = sheet.row_values(1)

        if "Hotel Name" not in headers:
            print("⚠️ 'Hotel Name' column missing in sheet.")
            return False, None

        col_chat = (
            headers.index("Telegram Chat ID") + 1
            if "Telegram Chat ID" in headers
            else len(headers) + 1
        )

        found_row = None
        hotel_data = None
        for idx, row in enumerate(records, start=2):
            if str(row.get("Hotel Name", "")).strip().lower() == hotel_name.strip().lower():
                found_row = idx
                hotel_data = row
                break

        if found_row:
            sheet.update_cell(found_row, col_chat, str(chat_id))
            print(f"✅ Updated Chat ID for '{hotel_name}' → {chat_id}")
            return "updated", hotel_data
        else:
            new_row = {
                "Hotel Name": hotel_name,
                "City": "",
                "Manager Email": "",
                "Telegram Chat ID": str(chat_id),
                "Sheet ID": "",
                "Phone": "",
                "Payment Link": "https://pay.guzoassist.com",
                "Availability": "Yes",
            }
            row_data = [new_row.get(h, "") for h in headers]
            sheet.append_row(row_data, value_input_option="USER_ENTERED")
            print(f"✅ Added new hotel '{hotel_name}' with Chat ID: {chat_id}")
            return "new", new_row

    except Exception as e:
        print(f"⚠️ Error adding or updating Chat ID for '{hotel_name}': {e}")
        return False, None


# ──────────────────────────────────────────────────────────────
async def register_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /register <Hotel Name>.
    Allows hotels to self-register automatically.
    """
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "Please type: /register <Hotel Name>\n\nExample: /register Sky Light Hotel"
        )
        return

    hotel_name = " ".join(args).strip()
    result, hotel_info = add_hotel_chat_id(hotel_name, chat_id)

    if not result:
        await update.message.reply_text(
            f"⚠️ Registration failed for '{hotel_name}'. Please check the spelling or contact Guzo Assist Support."
        )
        return

    city = hotel_info.get("City", "N/A") if hotel_info else "N/A"
    manager_email = hotel_info.get("Manager Email", "Not provided") if hotel_info else "Not provided"

    context.user_data["registered_hotel"] = {
        "name": hotel_name,
        "city": city,
        "manager_email": manager_email,
    }

    # ───── Welcome setup card ─────
    welcome_text = (
        f"🏨 **{hotel_name}** has been successfully registered with **Guzo Guest Assist**!\n\n"
        f"📍 City: {city}\n"
        f"📧 Manager Email: {manager_email}\n"
        f"📲 Chat ID: `{chat_id}`\n\n"
        f"💼 You’ll now receive all booking confirmations, reports, and guest messages here.\n\n"
        f"Use the button below to test your setup instantly 👇"
    )

    test_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🧪 Test Booking Message", callback_data=f"test_booking_card|{hotel_name}|{city}|{manager_email}")]]
    )

    await update.message.reply_text(
        welcome_text, reply_markup=test_button, parse_mode="Markdown"
    )

    print(f"🎉 Hotel '{hotel_name}' registered and welcome card sent to chat {chat_id}")


# ──────────────────────────────────────────────────────────────
async def handle_test_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the "🧪 Test Booking Message" button press.
    Sends a simulated booking summary including actual Hotel, City, and Manager Email.
    """
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    hotel_name = data[1] if len(data) > 1 else "Your Hotel"
    city = data[2] if len(data) > 2 else "Addis Ababa"
    manager_email = data[3] if len(data) > 3 else "manager@guzoassist.com"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confirmation_id = f"{hotel_name[:3].upper()}-TEST-{datetime.now().strftime('%H%M%S')}"
    guest_name = "John Doe"
    dates = "Oct 25–27, 2025"
    guests = "2 Adults"
    room = "Deluxe King Room"
    payment_link = "https://pay.guzoassist.com"

    demo_message = (
        f"📩 **New Guest Booking via Guzo Guest Assist**\n\n"
        f"🏨 **Hotel:** {hotel_name}\n"
        f"📍 **City:** {city}\n"
        f"👥 **Guests:** {guests}\n"
        f"📅 **Dates:** {dates}\n"
        f"🛏️ **Room Type:** {room}\n"
        f"🙍 **Guest Name:** {guest_name}\n"
        f"📧 **Manager Email:** {manager_email}\n"
        f"📱 **Phone:** +251911223344\n"
        f"🕒 **Time:** {now}\n"
        f"🔢 **Confirmation ID:** {confirmation_id}\n\n"
        f"💳 **Payment:** [Pay Securely Online]({payment_link})\n\n"
        f"✅ This is a *test message* confirming that your setup works correctly.\n"
        f"Real guest bookings will appear exactly like this — automatically from Guzo Guest Assist."
    )

    await query.edit_message_text(demo_message, parse_mode="Markdown")
    print(f"🧾 Sent test booking preview for {hotel_name}.")
