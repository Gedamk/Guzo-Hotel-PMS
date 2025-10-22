# -*- coding: utf-8 -*-
"""
reply_flow.py
Smart bilingual (English + Amharic) auto-reply engine for Guzo Guest Assist.
Integrates Ethiopian hospitality values and global professional etiquette.
"""

import re
from datetime import datetime
from guzo_booking_bot.utils.hotel_directory import fetch_hotel_data

def process_message(update, context):
    # ...handle incoming Telegram message...
    pass

def detect_language(text: str) -> str:
    """Detect basic language: Amharic vs English."""
    amharic_pattern = re.compile(r'[\u1200-\u137F]')
    return "amharic" if amharic_pattern.search(text) else "english"

def classify_message(text: str) -> str:
    """Determine message intent."""
    text_lower = text.lower()
    if any(word in text_lower for word in ["book", "reservation", "room", "night", "stay"]):
        return "booking"
    elif any(word in text_lower for word in ["cancel", "change", "modify"]):
        return "cancellation"
    elif any(word in text_lower for word in ["thank", "thanks", "appreciate"]):
        return "gratitude"
    elif any(word in text_lower for word in ["price", "rate", "cost"]):
        return "pricing"
    elif any(word in text_lower for word in ["hello", "hi", "good morning", "good evening"]):
        return "greeting"
    else:
        return "general"

def english_response(intent: str) -> str:
    """Compose professional English replies."""
    today = datetime.now().strftime("%A, %B %d")
    responses = {
        "greeting": f"👋 Hello! Thank you for contacting *Guzo Guest Assist*.\nHow may we help you today?",
        "booking": f"🛎️ Thank you for your booking request.\nOur reservation team will confirm your room shortly.\nDate: {today}",
        "cancellation": "We're sorry to hear you wish to cancel. Please confirm your reservation ID so we can assist you right away.",
        "pricing": "Our team will share current rates and offers shortly. Could you please specify your stay dates?",
        "gratitude": "You’re most welcome! It’s our pleasure to serve you.",
        "general": "Thank you for reaching out to *Guzo Guest Assist*. Our representative will reply soon."
    }
    return responses.get(intent, responses["general"])

def amharic_response(intent: str) -> str:
    """Compose polite Amharic replies (Ethiopian hospitality style)."""
    today = datetime.now().strftime("%A, %B %d")
    responses = {
        "greeting": "👋 ሰላም! እንኳን ወደ ጉዞ ጌስት አሲስት በደህና መጡ። እንዴት እንርዳዎታለን?",
        "booking": f"🛎️ ስለ ቦታ መያዝዎ እናመሰግናለን። ቦታዎ በቅርቡ ይረጋገጣል።\nቀን፡ {today}",
        "cancellation": "ስለ መሰረዝ መጠየቅዎ እናዝናለን። እባኮትን የቦታዎን መያዣ መለያ ያስገቡ።",
        "pricing": "የአሁኑ ዋጋ እና የቅናሽ መረጃዎች በቅርቡ ይላካሉ። እባኮትን የመኖሪያዎን ቀን ያስገቡ።",
        "gratitude": "እኛም እናመሰግናለን። ሁልጊዜ እንገልጻለን።",
        "general": "ስለ መግኘትዎ እናመሰግናለን። በቅርቡ ባለሙያ ባለሞያችን ይመልስዎታል።"
    }
    return responses.get(intent, responses["general"])

def generate_auto_reply(message: str) -> str:
    """Generate polite, bilingual, context-aware auto-reply."""
    language = detect_language(message)
    intent = classify_message(message)
    if language == "amharic":
        return amharic_response(intent)
    else:
        eng = english_response(intent)
        amh = amharic_response(intent)
        return f"{eng}\n\n{amh}\n\n— *Guzo Guest Assist Team*"

