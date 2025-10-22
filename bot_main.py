# -*- coding: utf-8 -*-
"""
bot_main.py â€“ Guzo Guest Assist (v6.0, Multilingual Concierge)
---------------------------------------------------------------
Stable multilingual booking bot with conversational flow,
auto-refreshing Google Sheets sync, and hotel registry display.
"""

import os
import sys
import asyncio
import platform
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
from guzo_booking_bot.modules.log_helper import log_event
from guzo_booking_bot.modules.conversational_booking_v6 import create_booking_conversation_handler

# --- Console Colors ---
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"

# -------------------------------------------------------------
# Environment setup
# -------------------------------------------------------------
load_dotenv()
LOCK_FILE = "bot.lock"

# -------------------------------------------------------------
# Prevent duplicate instances
# -------------------------------------------------------------
def clear_stale_lock():
    if os.path.exists(LOCK_FILE):
        try:
            import psutil
            active = any(
                "bot_main.py" in " ".join(p.info.get("cmdline", []))
                for p in psutil.process_iter(attrs=["pid", "cmdline"])
            )
            if not active:
                os.remove(LOCK_FILE)
                print(f"{CYAN}í·¹ Removed stale lock file.{RESET}")
        except Exception:
            os.remove(LOCK_FILE)
            print("Removed stale lock file (fallback).")

clear_stale_lock()
if os.path.exists(LOCK_FILE):
    print(f"{YELLOW}âš ï¸� Another instance of the bot is already running. Exiting safely.{RESET}")
    sys.exit(0)
open(LOCK_FILE, "w").close()
import atexit
atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))

# -------------------------------------------------------------
# Safe Hotel Registry Display
# -------------------------------------------------------------
def show_registered_hotels():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_booking_bot/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
        sheet = client.open_by_key(SHEET_ID).worksheet("Hotels")
        records = sheet.get_all_records()

        print(f"\n{CYAN}Hotel Registry (Google Sheet):{RESET}")
        print("------------------------------------------------------------")
        for row in records:
            name = row.get("Hotel Name", "(missing)")
            city = row.get("City", "(no city)")
            email = row.get("Manager Email", "(no email)")
            chat_id = row.get("Telegram Chat ID", "(no chat ID)")
            if chat_id not in ("", None, "(optional)"):
                status = f"{GREEN}âœ… Connected{RESET}"
            else:
                status = f"{YELLOW}âš ï¸� Missing Chat ID{RESET}"
            print(f"{name} | {city} | {email} | Chat ID: {chat_id} | {status}")
        print("------------------------------------------------------------\n")

    except Exception as e:
        print(f"{RED}Could not load hotel registry: {e}{RESET}")

# -------------------------------------------------------------
# Auto-refresh in background (every 10 minutes)
# -------------------------------------------------------------
async def safe_auto_refresh():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "guzo_booking_bot/creds/guzo_service_account.json", scope
        )
        client = gspread.authorize(creds)
        SHEET_ID = "13WD4nSsNLmYBnfEFCH7HhBmx2oP7uV4yaCGmHHfjTTM"
        sheet = client.open_by_key(SHEET_ID).worksheet("Hotels")
        records = sheet.get_all_records()

        print(f"{CYAN}Refreshing hotel registry from Google Sheet...{RESET}")
        for row in records:
            name = row.get("Hotel Name", "(missing)")
            chat_id = row.get("Telegram Chat ID", "(no chat ID)")
            if chat_id not in ("", None, "(optional)"):
                print(f"{GREEN}âœ… {name}: {chat_id}{RESET}")
            else:
                print(f"{YELLOW}âš ï¸� {name}: Missing Chat ID{RESET}")

    except Exception as e:
        print(f"{RED}Auto-refresh error: {e}{RESET}")

def start_auto_refresh(interval=10):
    async def loop_refresh():
        while True:
            await safe_auto_refresh()
            print(f"{CYAN}í´� Next auto-refresh in {interval} minutes...{RESET}")
            await asyncio.sleep(interval * 60)

    def runner():
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(loop_refresh())

    threading.Thread(target=runner, daemon=True).start()
    print(f"{GREEN}âœ… Auto-refresh enabled (every {interval} minutes).{RESET}")

# -------------------------------------------------------------
# Fallback handlers
# -------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "í±‹ Welcome to Guzo Guest Assist!\nPlease say 'Book a room' or 'áŠ­á��áˆ� áŠ¥á�ˆáˆ�áŒ‹áˆˆáˆ�' to start your booking."
    )
    log_event("BotMain", "INFO", "/start command used")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    log_event("BotMain", "MSG", f"{update.effective_user.first_name}: {text}")
    await update.message.reply_text("Please type 'book' or 'áŠ­á��áˆ�' to begin booking.")

# -------------------------------------------------------------
# Main bot runner
# -------------------------------------------------------------
def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print(f"{RED}Missing TELEGRAM_BOT_TOKEN in .env file.{RESET}")
        sys.exit(1)

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    show_registered_hotels()
    start_auto_refresh(10)

    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = create_booking_conversation_handler()
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print(f"{CYAN}Bot is running (Multilingual Concierge + Auto-Refresh)â€¦ Press Ctrl + C to stop.{RESET}")
    app.run_polling()

# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Bot stopped by user.{RESET}")
    except Exception as e:
        print(f"{RED}Critical bot error: {e}{RESET}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
