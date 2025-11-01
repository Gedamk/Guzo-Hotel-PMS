# -*- coding: utf-8 -*-
"""
bot_main.py – Guzo Guest Assist Telegram Bot
-------------------------------------------------
Natural-language, multilingual guest communication
for booking, payment, and assistance.
"""

import os, sys, logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

# ---------------------------------------------------------
# Environment Setup
# ---------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(PROJECT_ROOT), ".env")

load_dotenv(ENV_PATH, override=True)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ Missing TELEGRAM_BOT_TOKEN in .env file.")
    sys.exit(1)

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Multilingual Messages
# ---------------------------------------------------------
MESSAGES = {
    "en": {
        "welcome": (
            "👋 Welcome to *Guzo Guest Assist!*\n"
            "I'm here to help with your booking, payment, or hotel information.\n\n"
            "How can I assist you today?"
        ),
        "help": (
            "💬 I can help you with:\n"
            "• Room booking\n"
            "• Payment confirmation\n"
            "• Hotel information\n\n"
            "Just type what you need — no special commands required."
        ),
        "book_detected": "Great! Let’s start your booking process. 🏨",
        "pay_prompt": "💳 Sure! Please tell me your booking reference ID.",
        "pay_confirmed": "✅ Payment confirmed! Your invoice has been emailed.",
        "pay_failed": "⚠️ Payment could not be verified. Please contact support.",
        "unknown": "💬 Would you like to *book*, *pay*, or *get info*?",
    },
    "am": {
        "welcome": (
            "👋 እንኳን ወደ *Guzo Guest Assist* በደህና መጡ!\n"
            "በመያዣ፣ ክፍያ፣ ወይም በሌሎች ጥያቄዎች ላይ ለመርዳት እዚህ ነኝ።"
        ),
        "help": (
            "💬 እባክዎን እንዲህ እችላለሁ፦\n"
            "• መያዣ ማድረግ\n"
            "• ክፍያ ማረጋገጥ\n"
            "• የሆቴል መረጃ\n\n"
            "የሚፈልጉትን በቀጥታ ይጻፉ።"
        ),
        "book_detected": "ጥሩ ነው! የመያዣ ሂደትዎን እንጀምር። 🏨",
        "pay_prompt": "💳 እባክዎ የመያዣ ቁጥርዎን ይፃፉ።",
        "pay_confirmed": "✅ ክፍያዎ ተረጋግጧል። ደረሰኝዎ ተልኳል።",
        "pay_failed": "⚠️ ክፍያ አልተረጋገጠም። እባክዎ ያግኙን።",
        "unknown": "💬 መያዣ ይፈልጋሉ ወይም ክፍያ መፈጸም ነው?",
    },
}

# ---------------------------------------------------------
# Language Detector
# ---------------------------------------------------------
def detect_language(text: str) -> str:
    for ch in text:
        if "\u1200" <= ch <= "\u137F":  # Ethiopic range
            return "am"
    return "en"

# ---------------------------------------------------------
# Main Message Handler
# ---------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    lang = detect_language(text)
    msgs = MESSAGES.get(lang, MESSAGES["en"])

    # Greeting
    if any(w in text.lower() for w in ["hi", "hello", "hey", "selam", "ሰላም"]):
        await update.message.reply_text(msgs["welcome"], parse_mode="Markdown")
        return

    # Help
    if any(w in text.lower() for w in ["help", "assist", "ይርዱኝ", "እርዳታ"]):
        await update.message.reply_text(msgs["help"])
        return

    # Booking Intent
    if any(w in text.lower() for w in ["book", "reserve", "መያዣ", "ያዙ"]):
        await update.message.reply_text(msgs["book_detected"])
        await update.message.reply_text("🏨 Please tell me which hotel you’d like to book.")
        try:
            from guzo_booking_bot.modules.booking_handler import start_booking
            await start_booking(update, context)
        except Exception as e:
            logger.error(f"Booking flow error: {e}")
        return

    # Payment Intent
    if any(w in text.lower() for w in ["pay", "payment", "ክፍያ", "እከፍላለሁ"]):
        await update.message.reply_text(msgs["pay_prompt"])
        context.user_data["expecting_payment"] = True
        return

    # Payment Follow-up
    if context.user_data.get("expecting_payment"):
        ref = text.strip().upper()
        guest_name = update.effective_user.first_name or "Guest"
        guest_email = f"{guest_name.lower()}@guestmail.com"
        await update.message.reply_text(f"🔗 Generating secure payment link for {ref}...")

        try:
            from guzo_booking_bot.modules.payment_handler import process_payment
            success = process_payment(
                reference_id=ref,
                guest_name=guest_name,
                guest_email=guest_email,
                amount="850",
            )
            if success:
                await update.message.reply_text(msgs["pay_confirmed"])
            else:
                await update.message.reply_text(msgs["pay_failed"])
        except Exception as e:
            logger.error(f"Payment process failed: {e}")
            await update.message.reply_text(msgs["pay_failed"])

        context.user_data["expecting_payment"] = False
        return

    # Default Fallback
    await update.message.reply_text(msgs["unknown"], parse_mode="Markdown")

# ---------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------
def main():
    print("🚀 Loading Guzo Guest Assist Bot...")
    print("🔑 Token prefix:", BOT_TOKEN[:10])
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("🤖 Guzo Concierge Bot is running (natural chat, no /commands).")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"💥 Bot failed: {e}", exc_info=True)
        print(f"💥 Failed to start bot: {e}")

if __name__ == "__main__":
    main()
