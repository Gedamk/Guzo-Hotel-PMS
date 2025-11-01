# -*- coding: utf-8 -*-
"""
Auto Reply Module – Guzo Guest Assist (v4.1)
-----------------------------------------------------
Provides refined, bilingual hospitality responses (Amharic + English)
based on guest message sentiment and tone.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from langdetect import detect, DetectorFactory
from textblob import TextBlob
from datetime import datetime
from guzo_backend.modules import google_sheets

# =====================================================
# 🔹 Google Sheets Logging Helper
# =====================================================
def log_to_google_sheets(user: str, text: str, reply: str, lang: str, sentiment: float):
    """Save message interactions to Google Sheets Notifications Log."""
    try:
        sheet = google_sheets._open_sheet(
            google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
        )
        if sheet:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user,
                lang,
                f"{sentiment:.2f}",
                text,
                reply
            ])
            logger.info(f"✅ Logged message from {user} to Google Sheets.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to log to Google Sheets: {e}")

# =====================================================
# 🌍 Language Detection & Sentiment Setup
# =====================================================
DetectorFactory.seed = 0
logger = logging.getLogger("GuzoBot.AutoReply")

# -----------------------------
# Helper: Determine sentiment
# -----------------------------
def analyze_sentiment(message: str) -> float:
    """Returns sentiment polarity (-1 to 1)."""
    try:
        return TextBlob(message).sentiment.polarity
    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}")
        return 0.0

# -----------------------------
# Helper: Detect Language
# -----------------------------
def detect_language(text: str) -> str:
    """Detects if message is Amharic or English; defaults to English."""
    try:
        lang = detect(text)
        # Detect Amharic by Unicode range (U+1200 – U+137F)
        if "am" in lang or any("\u1200" <= ch <= "\u137F" for ch in text):
            return "am"
        return "en"
    except Exception:
        return "en"

# =====================================================
# 💬 Main Auto Reply Logic
# =====================================================
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user = update.effective_user.first_name if update.effective_user else "Guest"

    if not text:
        await update.message.reply_text("Hello! How may we assist you today?")
        return

    # Detect language + sentiment
    lang = detect_language(text)
    sentiment = analyze_sentiment(text)

    logger.info(f"📨 Received from {user}: '{text}' | Lang={lang} | Sentiment={sentiment:.2f}")

    # -----------------------------
    # English hospitality tone
    # -----------------------------
    if lang == "en":
        if sentiment <= -0.2:
            reply = (
                "We truly apologize for any inconvenience caused. "
                "Your comfort matters deeply to us, and our support team will reach out shortly."
            )
        elif sentiment >= 0.4:
            reply = (
                "Thank you for your kind message! We're delighted to hear from you. "
                "Our team will be in touch soon to ensure you're fully assisted."
            )
        else:
            reply = (
                "Warm greetings from Guzo Guest Assist 🌍\n"
                "Your message has been received, and we'll get back to you shortly. "
                "Thank you for choosing us to assist your stay."
            )

    # -----------------------------
    # Amharic hospitality tone
    # -----------------------------
    elif lang == "am":
        if sentiment <= -0.2:
            reply = (
                "እኛ በተፈጠረው አስቸጋሪ ሁኔታ ይቅርታ እንለዋለን። "
                "የእርስዎ መደሰት እጅግ አስፈላጊ ነው፣ ድጋፍ ቡድናችን በቅርቡ ያነጋግሮታል።"
            )
        elif sentiment >= 0.4:
            reply = (
                "ስለ በጎ መልእክትዎ እናመሰግናለን። "
                "የጉዞ ጌስት አሲስት ቡድን ደስ ብሎታል፣ በቅርቡ እንደሚረዳዎት ይረዳዎታል።"
            )
        else:
            reply = (
                "እንኳን ወደ ጉዞ ጌስት አሲስት በደህና መጡ 🌍\n"
                "መልእክትዎን ተቀብለናል፣ በቅርቡ እንመልስልዎታለን። "
                "ስለ ምርጫዎ እናመሰግናለን።"
            )

    # -----------------------------
    # Fallback tone (if detection fails)
    # -----------------------------
    else:
        reply = (
            "Thank you for reaching out to Guzo Guest Assist 🌍\n"
            "Your message has been received and logged for follow-up."
        )

    # =====================================================
    # 🚀 Send reply + log interaction
    # =====================================================
    await update.message.reply_text(reply)
    logger.info(f"✅ Sent reply to {user}: {reply[:60]}...")
    log_to_google_sheets(user, text, reply, lang, sentiment)
