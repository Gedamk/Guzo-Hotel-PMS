# -*- coding: utf-8 -*-
"""
telegram_group_audit.py
----------------------------------------------------
Align Telegram group data with Guzo Guest Assist Hotel Contacts Master.
----------------------------------------------------
"""

import os
import asyncio
import pandas as pd
from telegram import Bot
from dotenv import load_dotenv
from datetime import datetime
from guzo_booking_bot.modules import google_sheets

# Load environment variables
load_dotenv(dotenv_path=r"C:\Users\Gedan\Desktop\Guzo\.env", override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS_MASTER")
bot = Bot(token=TOKEN)

async def get_group_info():
    print("Fetching latest Telegram group updates...")
    updates = await bot.get_updates()

    if not updates:
        print("No recent messages found. Send a message in each hotel group first.")
        return

    records = []
    counter = 1

    for update in updates:
        chat = update.message.chat
        title = chat.title or "Private Chat"
        chat_id = chat.id

        try:
            admins = await bot.get_chat_administrators(chat_id)
            admin_names = ", ".join([a.user.first_name for a in admins])
        except Exception:
            admin_names = "Unknown"

        property_code = f"GUZ{counter:03d}"
        record = {
            "Hotel Name": title,
            "Property Code": property_code,
            "Location": "",
            "Sheet ID": "",
            "Main Contact Email": "",
            "Reservation Email": "",
            "Phone (Front Desk)": "",
            "Telegram Chat ID": chat_id,
            "GM / Hotel Manager Name": admin_names,
            "Preferred Language": "English",
            "Currency": "ETB",
            "Integration Status": "Active via Telegram",
        }
        records.append(record)
        counter += 1

    df = pd.DataFrame(records)
    print("\nAligned Hotel Contact Master Format:\n")
    print(df)

    # === Push results to Google Sheet ===
    try:
        print("\nSyncing to Google Sheet...")
        gc = google_sheets.init_client()
        workbook = gc.open_by_key(SHEET_ID)
        worksheet = workbook.sheet1
        worksheet.clear()
        worksheet.append_row(list(df.columns))
        for _, row in df.iterrows():
            worksheet.append_row(row.tolist())
        print("✅ Synced to Hotel Contacts Master successfully.")
    except Exception as e:
        print(f"⚠️ Could not sync to Google Sheet: {e}")

if __name__ == "__main__":
    asyncio.run(get_group_info())
