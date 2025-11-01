# -*- coding: utf-8 -*-
"""
auto_register.py
----------------------------------------------------
Automatically registers hotels when they run /register <Hotel Name>
and saves their Telegram Chat ID directly into Google Sheets.

After registration, sends a beautiful welcome setup card
with hotel info, Guzo Guest Assist logo emoji, and test button.
"""

import os
from dotenv import load_dotenv
import gspread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from guzo_booking_bot.modules.google_sheets import (
    init_client,
    get_hotel_contact_sheet_id,
)

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# Load environment variables
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def add_hotel_chat_id(hotel_name: str, chat_id: int):
    """
    Register or update a hotel's Telegram Chat ID in Hotel_Contacts_Master.
    - If the hotel exists â updates its Telegram Chat ID
    - If the hotel doesnât exist â adds a new row automatically
    """
    try:
        sheet_id = get_hotel_contact_sheet_id()
        if not sheet_id:
            print("â ï¸ No Hotel Contacts Master Sheet ID found in .env file.")
            return False

        client = init_client()
        if not client:
            print("â ï¸ Google Sheets client unavailable.")
            return False

        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_records()

        headers = sheet.row_values(1)
        if "Hotel Name" not in headers:
            print("â ï¸ 'Hotel Name' column missing in sheet.")
            return False

        col_chat = headers.index("Telegram Chat ID") + 1 if "Telegram Chat ID" in headers else len(headers) + 1

        found_row = None
        for idx, row in enumerate(records, start=2):
            if str(row.get("Hotel Name", "")).strip().lower() == hotel_name.strip().lower():
                found_row = idx
                break

        if found_row:
            sheet.update_cell(found_row, col_chat, str(chat_id))
            print(f"â Updated Chat ID for '{hotel_name}' â {chat_id}")
            return "updated"
        else:
            new_row = {
                "Hotel Name": hotel_name,
                "City": "",
                "Manager Email": "",
                "Telegram Chat ID": str(chat_id),
                "Sheet ID": "",
                "Phone": "",
            }
            row_data = [new_row.get(h, "") for h in headers]
            sheet.append_row(row_data, value_input_option="USER_ENTERED")
            print(f"â Added new hotel '{hotel_name}' with Chat ID: {chat_id}")
            return "new"

    except Exception as e:
        print(f"â ï¸ Error adding or updating Chat ID for '{hotel_name}': {e}")
        return False


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def register_hotel(update, context):
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
    result = add_hotel_chat_id(hotel_name, chat_id)

    if not result:
        await update.message.reply_text(
            f"â ï¸ Registration failed for '{hotel_name}'. Please check the spelling or contact Guzo Assist Support."
        )
        return

    # âââââ Welcome setup card âââââ
    welcome_text = (
        f"í¿¨ **{hotel_name}** has been successfully registered with **Guzo Guest Assist**!\n\n"
        f"í³² Chat ID: `{chat_id}`\n"
        f"í²¼ Youâll now receive all booking confirmations, reports, and guest messages here.\n\n"
        f"Use the button below to test your setup instantly í±"
    )

    test_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("í·ª Test Booking Message", callback_data="test_booking_card")]]
    )

    await update.message.reply_text(welcome_text, reply_markup=test_button, parse_mode="Markdown")

    print(f"í¾ Hotel '{hotel_name}' registered and welcome card sent to chat {chat_id}")


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async def handle_test_booking_callback(update, context):
    """
    Handles the "í·ª Test Booking Message" button press.
    Sends a simulated booking summary to confirm setup.
    """
    query = update.callback_query
    await query.answer()

    demo_message = (
        "í·¾ **Guzo Guest Assist Test Message**\n\n"
        "This confirms that your hotel setup is working correctly â\n\n"
        "When a guest books a room, this chat will receive automatic booking details,\n"
        "emails will be sent to your manager address, and the booking will be logged in Google Sheets.\n\n"
        "Youâre all set to start receiving live bookings í¾"
    )

    await query.edit_message_text(demo_message, parse_mode="Markdown")
