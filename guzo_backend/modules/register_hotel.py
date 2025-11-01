# -*- coding: utf-8 -*-
"""
register_hotel.py ‚Äì Handles /register command for hotel managers
---------------------------------------------------------------
Adds hotel info to Google Sheet "Hotels" tab of Guzo_System_Master
"""

import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from guzo_backend.modules import google_sheets   # must exist

load_dotenv()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID_GUZO_SYSTEM")

async def register_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a new hotel when manager sends /register <HotelName>"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text("‚ö†Ô∏è Please provide a hotel name, e.g.\n/register Sky Light Hotel")
        return

    hotel_name = " ".join(args)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet = google_sheets._open_sheet(GOOGLE_SHEET_ID, "Hotels")
    sheet.append_row([
        f"H-{str(chat_id)[-4:]}",  # simple hotel ID
        hotel_name,
        str(chat_id),
        user.full_name,
        "", "", now, "Active"
    ])

    await update.message.reply_text(
        f"‚úÖ Hotel registered successfully!\nÌø® {hotel_name}\nÌ±§ Manager: {user.full_name}\nÌµì {now}"
    )
