# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Multi-Channel Bot
-------------------------------------
Main Telegram entry point for Guzo Guest Assist.
Handles guest and hotel messages, registration, and routing.

Supports:
- Central bot using project root .env
- Per-property bots using GUZO_BOT_ENV_PATH to load hotel-specific .env
"""

import os
import sys
import logging
import asyncio

from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================================================
# PATH SETUP
# ======================================================

# ✅ BASE_DIR = project root (Guzo/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# ======================================================
# ENV + UTF-8
# ======================================================

# 1) Load ROOT env from project root: Guzo/.env
ROOT_ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ROOT_ENV_PATH)

# 2) Optional: override with hotel-specific .env (for property bots)
GUZO_BOT_ENV_PATH = os.getenv("GUZO_BOT_ENV_PATH")
if GUZO_BOT_ENV_PATH:
    # Allow relative paths from project root as well
    if not os.path.isabs(GUZO_BOT_ENV_PATH):
        GUZO_BOT_ENV_PATH = os.path.join(BASE_DIR, GUZO_BOT_ENV_PATH)

    if os.path.exists(GUZO_BOT_ENV_PATH):
        load_dotenv(GUZO_BOT_ENV_PATH, override=True)
        print(f"[ENV] Loaded hotel-specific env from: {GUZO_BOT_ENV_PATH}")
    else:
        print(f"[ENV] WARNING: GUZO_BOT_ENV_PATH set but file not found: {GUZO_BOT_ENV_PATH}")

telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "CENTRAL")
HOTEL_PROPERTY_CODE = os.getenv("HOTEL_PROPERTY_CODE", "ALL")

if not telegram_token:
    print("❌ TELEGRAM_BOT_TOKEN missing in env. Check .env / GUZO_BOT_ENV_PATH.")
    sys.exit(1)

# ✅ UTF-8 output fix
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # Older Python / weird terminals – just ignore
    pass

# ======================================================
# LOGGING
# ======================================================

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    format="%(asctime)s - GuzoBot - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(
            os.path.join(BASE_DIR, "logs", "bot.log"), encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("GuzoBot")

logger.info(f"Bot mode: {BOT_MODE}, HOTEL_PROPERTY_CODE={HOTEL_PROPERTY_CODE}")
logger.info(f"GUZO_BOT_ENV_PATH={GUZO_BOT_ENV_PATH}")

if HOTEL_PROPERTY_CODE.upper() == "ALL":
    logger.warning(
        "HOTEL_PROPERTY_CODE is 'ALL'. Make sure your backend supports central "
        "routing for this, or set a real property code like DRE001 / N&N002."
    )

# ======================================================
# INTERNAL IMPORTS
# ======================================================

# ⚠️ IMPORTANT: import the *module*, not process_message directly
import guzo_booking_bot.modules.message_router as message_router

# /register command – hotel onboarding
from guzo_backend.modules.register_hotel import register_hotel

# ======================================================
# ROUTER WRAPPER (ASYNC-SAFE)
# ======================================================

async def process_message_async(update, context: ContextTypes.DEFAULT_TYPE):
    """
    Async wrapper around guzo_booking_bot.modules.message_router.handle_message.

    Expected backend signature:
        handle_message(update, context, property_code)

    We ALWAYS pass HOTEL_PROPERTY_CODE (from env).
    The router + DB decide what to do with that code
    (single-property vs ALL/central).
    """
    logger.info(
        "process_message wrapper – BOT_MODE=%s, HOTEL_PROPERTY_CODE=%s",
        BOT_MODE,
        HOTEL_PROPERTY_CODE,
    )

    try:
        # Always call with property_code: matches router signature
        result = message_router.handle_message(update, context, HOTEL_PROPERTY_CODE)
    except Exception as e:
        logger.error(
            "Error while calling handle_message(update, context, "
            "property_code=%r): %s",
            HOTEL_PROPERTY_CODE,
            e,
        )
        return (
            "⚠️ Internal routing error in Guzo bot.\n"
            "Please try again in a few minutes."
        )

    # If router returned a coroutine, await it
    if asyncio.iscoroutine(result):
        try:
            result = await result
        except Exception as e2:
            logger.error("Error while awaiting router coroutine: %s", e2)
            return (
                "⚠️ Internal routing error in Guzo bot.\n"
                "Please try again in a few minutes."
            )

    return result

# ======================================================
# TELEGRAM HANDLERS
# ======================================================

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when /start command is issued."""
    user = update.effective_user
    logger.info(
        "Started chat with %s",
        user.username or user.id,
    )

    await update.message.reply_text(
        "👋 Welcome to Guzo Guest Assist!\n"
        "How can we help you today?"
    )


async def handle_text(update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all incoming guest/hotel messages and routes them."""
    user = update.effective_user
    text = update.message.text.strip() if update.message and update.message.text else ""
    logger.info("Message from %s: %s", user.username or user.id, text)

    try:
        # ✅ Call async wrapper and await it
        response = await process_message_async(update, context)

        # If router returns a message, send it back
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "🤖 Thank you! Your request is being processed."
            )

    except Exception as e:
        logger.exception("Error while processing message: %s", e)
        await update.message.reply_text(
            "⚠️ Sorry, something went wrong while processing your message."
        )

# ======================================================
# MAIN FUNCTION
# ======================================================

def main():
    """Starts the Telegram bot."""
    try:
        logger.info("🚀 Launching Telegram Bot...")
        application = ApplicationBuilder().token(telegram_token).build()

        # 🔹 Register command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register_hotel))

        # 🔹 Generic text handler → routes via message_router / backend
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
        )

        print("🤖 Guzo Guest Assist Telegram bot is running...")
        application.run_polling()

    except Exception as e:
        logger.error("❌ Fatal error: %s", e)
        print(f"❌ Fatal error: {e}")

# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":
    main()
