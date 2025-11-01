# -*- coding: utf-8 -*-
"""
message_router.py – Guzo Guest Assist (v14.0)
------------------------------------------------
Multilingual (English + Amharic) + Voice-enabled Telegram assistant.
Auto-detects guest language, transcribes voice messages, and routes
requests to Google Sheets + Email confirmations.
"""

import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from langdetect import detect, DetectorFactory
from guzo_backend.modules import google_sheets, auto_confirmation
from guzo_backend.modules.voice_handler import handle_voice

DetectorFactory.seed = 0  # deterministic language detection

# ======================================================
# 💬 INTENT DETECTION
# ======================================================
def detect_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["book", "room", "stay", "reserve", "check-in", "night", "booking", "መያዣ", "መያዣዬ"]):
        return "booking"
    if any(w in msg for w in ["cancel", "change", "modify", "reschedule", "refund", "መሰረዝ", "መቀየር"]):
        return "cancellation"
    return "general"


# ======================================================
# 🌍 SMART MULTILINGUAL RESPONSE BUILDER
# ======================================================
def build_smart_response(intent: str, hotel_name: str, guest_name: str, lang: str):
    """Generate reply text dynamically based on detected language."""
    if intent == "booking":
        eng = (
            f"🛎️ Dear {guest_name}, thank you for choosing {hotel_name}.\n"
            "Your booking request has been received and is being processed.\n"
            "We’ll confirm shortly.\n\n— Guzo Guest Assist"
        )
        amh = (
            f"🛎️ ውድ {guest_name}፣ ስለ {hotel_name} መያዣዎ እናመሰግናለን። "
            "መያዣዎ ተቀብያለች፣ በቅርቡ ይረጋገጣል።\n\n— ጉዞ ገስት አሲስት"
        )
    elif intent == "cancellation":
        eng = (
            f"❌ Dear {guest_name}, we’ve received your cancellation request for {hotel_name}. "
            "Your booking will be updated soon.\n\n— Guzo Guest Assist"
        )
        amh = (
            f"❌ ውድ {guest_name}፣ የ {hotel_name} መያዣዎን ለመሰረዝ ጥያቄዎን ተቀብያለን። "
            "በቅርቡ ይዘምናል።\n\n— ጉዞ ገስት አሲስት"
        )
    else:
        eng = (
            f"💬 Dear {guest_name}, thank you for contacting Guzo Guest Assist.\n"
            "Your message has been received. We’ll respond soon.\n\n— Guzo Guest Assist"
        )
        amh = (
            f"💬 ውድ {guest_name}፣ እናመሰግናለን። ጥያቄዎን ተቀብያለን። "
            "በቅርቡ እንመልስልዎታለን።\n\n— ጉዞ ገስት አሲስት"
        )

    # Language-based output
    if lang.startswith("am"):
        return amh
    elif lang.startswith("en"):
        return eng
    else:
        return f"{eng}\n\n{amh}"


# ======================================================
# ✉️ TEXT MESSAGE HANDLER
# ======================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    guest_name = user.full_name or "Guest"

    # Language detection
    try:
        lang = detect(text)
    except Exception:
        lang = "en"

    intent = detect_intent(text)
    words = text.split()
    hotel_name = " ".join([w for w in words if w.istitle()]) or "Your Hotel"

    response = build_smart_response(intent, hotel_name, guest_name, lang)
    await update.message.reply_text(response, parse_mode="Markdown")

    # Log + confirmation
    google_sheets.log_new_request(guest_name, hotel_name, text, status=intent)
    await auto_confirmation.confirm_guest_request(
        guest_name=guest_name,
        hotel_name=hotel_name,
        message=text,
        recipient_email="manager@sofihotel.com",
    )


# ======================================================
# 🚀 MAIN BOT APP ENTRYPOINT
# ======================================================
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Missing TELEGRAM_BOT_TOKEN in .env")
        return

    google_sheets.init_client()
    app = ApplicationBuilder().token(token).build()

    # Text + Voice handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("🤖 Guzo Guest Assist Bot (v14) running – text + voice multilingual support active.")
    app.run_polling()


if __name__ == "__main__":
    main()
