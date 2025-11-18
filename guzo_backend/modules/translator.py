# -*- coding: utf-8 -*-
"""
translator.py – Guzo Guest Assist Global Translator (v75.0)
-----------------------------------------------------------
🌍 Central multilingual communication module for hospitality chatbots.

Supported Languages:
- English (en)
- Amharic (am)
- Afaan Oromo (om)

Functions:
✅ detect_language(text) – Detect user message language
✅ translate_text(text, target_lang) – Translate text automatically
✅ get_standard_message(tag, lang) – Return polite, pre-translated templates for hospitality

Uses Deep Translator (GoogleTranslator) for fallback translation.
"""

import logging
from langdetect import detect
from deep_translator import GoogleTranslator

# ============================================================
# SUPPORTED LANGUAGES
# ============================================================
SUPPORTED_LANGUAGES = ["en", "am", "om"]
DEFAULT_LANG = "en"

# ============================================================
# LANGUAGE DETECTION
# ============================================================
def detect_language(text: str) -> str:
    """Detect the language code from user input."""
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANG
    except Exception as e:
        logging.warning(f"[Translator] Language detection failed: {e}")
        return DEFAULT_LANG

# ============================================================
# TRANSLATION FUNCTION
# ============================================================
def translate_text(text: str, target_lang: str) -> str:
    """Translate text using Deep Translator."""
    if not text or target_lang == "en":
        return text
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated
    except Exception as e:
        logging.warning(f"[Translator] Fallback translation used due to: {e}")
        return text

# ============================================================
# STANDARDIZED HOSPITALITY MESSAGES
# ============================================================
TEMPLATES = {
    "welcome": {
        "en": "👋 Welcome to our hotel! How may we assist you today?",
        "am": "👋 እንኳን ወደ ሆቴላችን በደህና መጡ። እንዴት እንርዳዎታለን?",
        "om": "👋 Baga gara hooteel keenyaatti dhuftan! Akkam si gargaaruu dandeenya?",
    },
    "thank_you": {
        "en": "🙏 Thank you for choosing Guzo Guest Assist.",
        "am": "🙏 እናመሰግናለን ስለመርጠው Guzo Guest Assist።",
        "om": "🙏 Galatoomi Guzo Guest Assist filattee.",
    },
    "booking_confirmed": {
        "en": "✅ Your booking is confirmed. We look forward to welcoming you soon!",
        "am": "✅ መያዣዎ ተረጋግጧል። በቅርቡ መቀበልዎን እንጠብቃለን!",
        "om": "✅ Bookingi kee mirkanaa’eera. Baga nu bira dhufuu!",
    },
    "booking_pending": {
        "en": "🕓 Your booking request has been received and is being processed.",
        "am": "🕓 የመያዣ ጥያቄዎ ተቀብሏል እና በሂደት ላይ ነው።",
        "om": "🕓 Gaaffiin bookingii kee argameera, itti fufa jira.",
    },
    "apology": {
        "en": "⚠️ Sorry, something went wrong. Please try again.",
        "am": "⚠️ ይቅርታ፣ ችግር ተፈጥሯል። እባክዎን ደግመው ይሞክሩ።",
        "om": "⚠️ Dhiifama, dogoggorri uumameera. Irra deebi’i yaali.",
    },
    "farewell": {
        "en": "👋 Thank you for staying with us! We hope to see you again soon.",
        "am": "👋 ከእኛ ጋር ስለቆዩ እናመሰግናለን። በቅርቡ እንድንያይዎ እንመኛለን።",
        "om": "👋 Nuti waliin turteetta. Yeroo biraa si arguuf hawwina!",
    },
    "ask_language": {
        "en": "🌐 Please select your preferred language.",
        "am": "🌐 እባክዎን የተመረጡትን ቋንቋ ይምረጡ።",
        "om": "🌐 Afaan filattee fayyadami.",
    },
    "error_invalid_date": {
        "en": "⚠️ Invalid date format. Please use YYYY-MM-DD.",
        "am": "⚠️ የቀን ቅርጸት ትክክል አይደለም። እባክዎን YYYY-MM-DD ይጠቀሙ።",
        "om": "⚠️ Guyyaan sirrii miti. Maaloo YYYY-MM-DD fayyadami.",
    },
    "error_invalid_input": {
        "en": "⚠️ Sorry, I didn’t catch that. Please choose from the options.",
        "am": "⚠️ ይቅርታ፣ ያ አልተረዳኩም። እባክዎን ከአማራጮቹ ይምረጡ።",
        "om": "⚠️ Dhiifama, wanti jettu hin hubatamne. Filannoo keessaa filadhu.",
    },
}

# ============================================================
# TEMPLATE FETCHER
# ============================================================
def get_standard_message(tag: str, lang: str = "en") -> str:
    """Return hospitality-standard multilingual message."""
    try:
        lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANG
        if tag in TEMPLATES:
            return TEMPLATES[tag].get(lang, TEMPLATES[tag].get("en"))
        else:
            logging.warning(f"[Translator] Unknown tag: {tag}")
            return TEMPLATES["apology"].get(lang)
    except Exception as e:
        logging.error(f"[Translator] Failed to get message for tag {tag}: {e}")
        return "⚠️ System error."


# ============================================================
# TEST EXECUTION
# ============================================================
if __name__ == "__main__":
    print("🌍 Translator module test run:")
    samples = [
        ("Welcome to our hotel!", "am"),
        ("Welcome to our hotel!", "om"),
        ("Thank you", "am"),
        ("See you again", "om"),
    ]
    for text, lang in samples:
        print(f"\n🔸 Original: {text}\n🔹 Translated ({lang}): {translate_text(text, lang)}")

    print("\n✅ Template test:")
    for tag in ["welcome", "thank_you", "booking_confirmed", "farewell"]:
        print(f"{tag} (am):", get_standard_message(tag, "am"))
        print(f"{tag} (om):", get_standard_message(tag, "om"))
