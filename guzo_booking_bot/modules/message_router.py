# -*- coding: utf-8 -*-
"""message_router.py — Guzo Guest Assist Bot (Global Hospitality + Analytics Edition, emoji-safe build)"""

import os, logging, datetime
from langdetect import detect
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from guzo_booking_bot.modules import google_sheets, email_sender

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/message_router.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

RESPONSES = {
    "en": {
        "welcome": "\U0001F44B Welcome to Guzo Guest Assist! How may we help you today?",
        "confirm": "\u2705 Your request has been received and logged. Our guest team will contact you shortly.",
        "error": "\u26A0\uFE0F We're sorry — something went wrong while processing your request. Please try again later."
    }
}

def main():
    print("🚀 Guzo Guest Assist Bot initialized successfully!")
    print("🤖 Bot is ready for multilingual guest messages worldwide.")
    # (Bot logic continues...)

if __name__ == "__main__":
    main()
