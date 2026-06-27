# -*- coding: utf-8 -*-
"""
hotel_concierge.py – Guzo Guest Assist Smart Concierge (v9.5)
--------------------------------------------------------------
🌍 Global-standard bilingual (English + Amharic) conversational AI
for hotels using the Guzo Guest Assist platform.

Features:
--------------------------------------------------------------
✅ Natural-language understanding (keywords + fuzzy detection)
✅ Emotion-aware responses with service recovery
✅ Google Sheets data integration
✅ Automatic fallback: hotel contact & website
✅ Eco-friendly sustainability messages
✅ Admin alert for dissatisfaction
✅ Global hospitality tone and etiquette
"""
import os
import re
import random
from difflib import get_close_matches
from guzo_booking_bot.modules import telegram_notifier, sentiment_analyzer, sustainability_tips

# ---------------------------------------------------------------------
# DEFAULT CONCIERGE RESPONSES (GLOBAL STANDARD)
# ---------------------------------------------------------------------
ENGLISH_DEFAULTS = {
    "wifi": "🌐 Wi-Fi is complimentary throughout the hotel. The password is provided at check-in or you can ask the front desk anytime.",
    "breakfast": "🍳 Breakfast is served daily from 6:30 AM – 10:30 AM in the restaurant on the ground floor.",
    "checkin": "🕓 Check-in time starts at 2:00 PM. Early check-in is subject to availability.",
    "checkout": "🕛 Check-out time is 12:00 noon. Late check-out may be available upon request.",
    "transport": "🚖 Airport shuttle service operates hourly. Please confirm your flight time for pickup.",
    "restaurant": "🍽️ The hotel restaurant is open from 7:00 AM – 11:00 PM, offering both local and international cuisine.",
    "attraction": "🎯 Nearby attractions include Friendship Business Center, Medhane Alem Cathedral, and Edna Mall.",
    "default": "💁 Thank you for your message. Our team will respond shortly. Meanwhile, here’s some information about our main services."
}

AMHARIC_DEFAULTS = {
    "wifi": "🌐 ዊፋይ በሆቴሉ ሁሉ ቦታ ነፃ ነው። የዊፋይ ፓስዎርድ በመግቢያ ጊዜ ይሰጣል።",
    "breakfast": "🍳 ቁርስ በየቀኑ ከ6:30 እስከ 10:30 ድረስ በሬስቶራንቱ ይሰራል።",
    "checkin": "🕓 መግቢያ ሰዓት ከ2፡00 በኋላ ነው። ቀደም ብሎ መግቢያ ከተፈቀደ ጋር ይቻላል።",
    "checkout": "🕛 መውጫ ሰዓት 12፡00 ቀን ነው። በተጠየቀ ጊዜ ተጨማሪ ሰዓት ይሰጣል።",
    "transport": "🚖 የአየር መንገድ መኪና አገልግሎት በየሰዓቱ ይሰራል። የበረራ ጊዜዎን እባክዎን ያረጋግጡ።",
    "restaurant": "🍽️ ሬስቶራንቱ ከ7፡00 እስከ 11፡00 ድረስ ክፍት ነው። አካባቢያዊና ዓለም አቀፍ ምግቦችን ያቀርባል።",
    "attraction": "🎯 በአቅራቢያው ያሉ መዝናኛዎች፦ እድና ማል፣ መድሃኔ አለም ቤተ ክርስቲያን እና ፍሬንድሺፕ ቢዝነስ ማዕከል።",
    "default": "💁 እናመሰግናለን። መልእክትዎን ተቀብለናል። የቡድናችን አባል በቅርቡ ይመልስልዎታል።"
}

# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def fetch_hotel_custom_responses(sheet_id: str):
    """Google Sheets disabled; return no custom sheet overrides."""
    return {}


def get_hotel_marketing_profile(property_code: str = "DRE001"):
    """Static fallback until marketing profiles are exposed by the backend."""
    return {
        "property_code": property_code,
        "hotel_name": "Dream Big Hotel",
        "description": "A luxury hospitality property managed through Guzo PMS.",
        "amenities": [
            "Front desk support",
            "Room booking support",
            "Housekeeping request",
            "Maintenance request",
            "Restaurant and local information",
        ],
        "phone": "",
        "website": "",
    }

# ---------------------------------------------------------------------
# MAIN CONCIERGE LOGIC
# ---------------------------------------------------------------------
def get_concierge_reply(hotel_name: str, user_message: str, lang: str = "en", sheet_id: str = None) -> str:
    """
    Smart sentiment-aware multilingual concierge response.
    Fallbacks to contact + website if no topic match found.
    """
    msg = user_message.lower().strip()
    lang = "am" if re.search("[አ-ፐ]", msg) else lang
    defaults = ENGLISH_DEFAULTS if lang == "en" else AMHARIC_DEFAULTS
    custom = fetch_hotel_custom_responses(sheet_id) if sheet_id else {}

    keyword_map = {
        "wifi": ["wifi", "wi-fi", "internet", "connection", "ዊፋይ"],
        "breakfast": ["breakfast", "morning", "food", "ቁርስ"],
        "checkin": ["checkin", "check-in", "arrive", "መግቢያ"],
        "checkout": ["checkout", "check-out", "leave", "መውጫ"],
        "transport": ["taxi", "car", "airport", "transport", "መኪና"],
        "restaurant": ["restaurant", "dining", "lunch", "dinner", "ምግብ"],
        "attraction": ["attraction", "visit", "tour", "place", "መዝናኛ"],
    }

    matched_key = None
    for key, synonyms in keyword_map.items():
        if any(s in msg for s in synonyms):
            matched_key = key
            break

    # --- Sentiment check (service recovery SOP) ---
    mood = sentiment_analyzer.analyze(user_message)
    if mood == "negative":
        apology = (
            "🙏 We’re truly sorry for the inconvenience. "
            "Your comfort is our priority, and we’ve notified the hotel team to improve this immediately."
            if lang == "en" else
            "🙏 ይቅርታ፣ ለተፈጠረው እንደምን እናሳዝናለን። የእርስዎን የአሳማኝነት ሁኔታ ለቡድናችን አስታውቀናል።"
        )
        telegram_notifier.notify_admin(
            f"⚠️ Guest dissatisfaction detected at {hotel_name}:\n“{user_message}”"
        )
    else:
        apology = ""

    # --- Determine reply ---
    if matched_key:
        reply = custom.get(matched_key, {}).get(lang) or defaults.get(matched_key, defaults["default"])
    else:
        # Fallback to fuzzy match
        all_words = sum(keyword_map.values(), [])
        close = get_close_matches(msg, all_words, n=1, cutoff=0.6)
        if close:
            key_guess = next((k for k, v in keyword_map.items() if close[0] in v), None)
            reply = defaults.get(key_guess, defaults["default"])
        else:
            reply = defaults["default"]

        profile = get_hotel_marketing_profile()
        contact = profile.get("website", "")
        phone = profile.get("phone", "")
        if phone or contact:
            reply += f"\n\n📞 For more assistance, please contact us at {phone} or visit {contact}."

    eco_tip = sustainability_tips.random_tip(lang)
    return f"{apology}\n{reply}\n\n{eco_tip}"
