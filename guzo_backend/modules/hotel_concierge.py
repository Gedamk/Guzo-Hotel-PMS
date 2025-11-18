# -*- coding: utf-8 -*-
"""
hotel_concierge.py – Guzo Guest Assist Concierge Logic
-------------------------------------------------------
Handles guest messages, concierge requests, and multilingual replies.
"""

def get_concierge_reply(hotel_name: str, message_text: str, lang: str = "en") -> str:
    """
    Generate a smart concierge reply based on hotel name, message, and language.
    """
    message_lower = message_text.lower()

    # Optional: use hotel_name in responses if needed
    if "wifi" in message_lower:
        return (
            f"📶 The Wi-Fi password at {hotel_name} is available at the front desk."
            if lang == "en"
            else f"📶 የዊፋይ ፓስዎርድ በ {hotel_name} ፊት ዴስክ ላይ ይገኛል።"
        )

    elif "breakfast" in message_lower:
        return (
            f"🍳 Breakfast is served from 6:30 AM to 10:00 AM at {hotel_name}'s main restaurant."
            if lang == "en"
            else f"🍳 ቁርስ ከ6:30 እስከ10:00 በ {hotel_name} ዋናው ሬስቶራንት ይሰራል።"
        )

    elif "checkout" in message_lower:
        return (
            "🕒 Checkout time is 12:00 PM. Please contact the front desk for late checkout requests."
            if lang == "en"
            else "🕒 የመውጫ ሰዓት 12:00 ነው። ለተጨማሪ ጊዜ የመውጫ ጥያቄ ከፊት ዴስክ ጋር ይወያዩ።"
        )

    elif "restaurant" in message_lower or "dinner" in message_lower:
        return (
            "🍽️ The main restaurant is open from 12:00 PM to 10:30 PM."
            if lang == "en"
            else "🍽️ ዋናው ሬስቶራንት ከ12:00 እስከ10:30 ድረስ ክፍት ነው።"
        )

    else:
        return (
            f"🤖 Thank you for your message. {hotel_name}'s concierge will respond shortly."
            if lang == "en"
            else f"🤖 እናመሰግናለን። የ {hotel_name} ኮንስየርዝ በቅርቡ ይመልስልዎታል።"
        )
