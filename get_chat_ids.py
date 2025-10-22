# -*- coding: utf-8 -*-
"""
get_chat_ids.py – List and auto-update Telegram chat IDs for Guzo Guest Assist
-------------------------------------------------------------------------------
This helper script lists all Telegram chat IDs (private, group, supergroup)
where your bot has interacted. It can also automatically update your
Google Sheet registry with the correct chat IDs.

Usage:
    python get_chat_ids.py
"""

import os
import telegram
import asyncio
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Load environment variables (Telegram token)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN missing in .env file.")
    exit()

bot = telegram.Bot(token=TOKEN)

# ✅ Google Sheet configuration
SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
TAB_NAME = "Hotels"


def update_sheet(chat_id, chat_name):
    """
    Automatically update the 'Telegram Chat ID' column in the Google Sheet
    if the chat name matches a hotel name.
    """
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_booking_bot/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(TAB_NAME)
        records = sheet.get_all_records()

        found = False
        for i, row in enumerate(records, start=2):  # Skip header row
            hotel_name = row.get("Hotel Name", "").strip().lower()
            if hotel_name and hotel_name in chat_name.lower():
                col_index = list(row.keys()).index("Telegram Chat ID") + 1
                sheet.update_cell(i, col_index, str(chat_id))
                print(f"[UPDATED] {hotel_name} → Chat ID {chat_id}")
                found = True
                break

        if not found:
            print(f"[WARN] No matching hotel for '{chat_name}' in the sheet.")
    except Exception as e:
        print(f"[ERROR] Google Sheets update failed: {e}")


async def main():
    print("[INFO] Fetching Telegram chat updates...")
    updates = await bot.get_updates()

    if not updates:
        print("[WARN] No updates found. Send /start or /book to your bot first.")
        return

    seen = set()
    for u in updates:
        if not u.message:
            continue

        chat = u.message.chat
        if chat.id in seen:
            continue
        seen.add(chat.id)

        chat_name = chat.title or chat.first_name or "Unnamed"
        chat_type = chat.type

        print(f"[CHAT] ID: {chat.id} | Type: {chat_type} | Name: {chat_name}")
        update_sheet(chat.id, chat_name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[EXIT] Operation cancelled by user.")
