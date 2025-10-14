# -*- coding: utf-8 -*-
"""
reply_flow.py
Personalized bilingual auto-reply engine for Guzo Guest Assist.
Integrates Ethiopian hospitality values, hotel profile, and polite global tone.
"""

import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load hotel info from environment variables
load_dotenv()
HOTEL_NAME = os.getenv("HOTEL_NAME", "Your Hotel")
MANAGER_NAME = os.getenv("MANAGER_NAME", "The Manager")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "info@guzoassist.com")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+251900000000")

def detect_language(text: str) -> str:
    """Detect Amharic vs English."""
    amharic_pattern = re.compile(r'[\u1200-\u137F]')
    return "amharic" if amharic_pattern.search(text) else "english"

def classify_message(text: str) -> str:
    """Categorize message intent."""
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
    """Professional English auto-reply with personalization."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    responses = {
        "greeting": f"👋 Hello! Welcome to {HOTEL_NAME}. How may we assist you today?",
        "booking": (
            f"🛎️ Thank you for your booking request at *{HOTEL_NAME}*.\n"
            f"Our reservation team will confirm your room shortly.\n"
            f"Date: {today}\n\nFor urgent assistance: {SUPPORT_PHONE}"
        ),
        "cancellation": (
            f"We’re sorry to hear you wish to cancel your stay at {HOTEL_NAME}.\n"
            f"Please confirm your booking ID so we can assist right away."
        ),
        "pricing": (
            f"Our team will share available rates and offers soon.\n"
            f"Could you please specify your stay dates?"
        ),
        "gratitude": (
            f"You’re most welcome! On behalf of {HOTEL_NAME}, we appreciate your kind words.\n"
            f"Warm regards, {MANAGER_NAME}"
        ),
        "general": (
            f"Thank you for contacting {HOTEL_NAME}.\n"
            f"Our representative will reply shortly.\n"
            f"📧 {SUPPORT_EMAIL} | ☎️ {SUPPORT_PHONE}"
        )
    }
    return responses.get(intent, responses["general"])

def amharic_response(intent: str) -> str:
    """Warm, polite Amharic auto-reply with local hospitality values."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    responses = {
        "greeting": f"👋 እንኳን ወደ {HOTEL_NAME} በደህና መጡ። እንዴት እንርዳዎታለን?",
        "booking": (
            f"🛎️ ስለ ቦታ መያዝዎ እናመሰግናለን።\n"
            f"ቦታዎ በቅርቡ ይረጋገጣል። ቀን፡ {today}\n"
            f"ለአስቸኳይ ጥያቄዎች፡ {SUPPORT_PHONE}"
        ),
        "cancellation": (
            f"ስለ መሰረዝ መጠየቅዎ እናዝናለን። "
            f"እባኮትን የቦታዎን መያዣ መለያ ያስገቡ።"
        ),
        "pricing": (
            f"የአሁኑ ዋጋዎች እና ቅናሾች በቅርቡ ይላካሉ። "
            f"እባኮትን የመኖሪያዎን ቀን ያስገቡ።"
        ),
        "gratitude": (
            f"እኛም እናመሰግናለን። "
            f"በመንግሥትና በህዝብ ልማድ መሠረት የተባበረ አገልግሎት እንሰጣለን።\n"
            f"ከተወዳጅ ተቆጣጣሪ፡ {MANAGER_NAME}"
        ),
        "general": (
            f"እናመሰግናለን ስለ መግኘትዎ። "
            f"በቅርቡ ባለሙያችን ይመልስዎታል።\n"
            f"ኢሜል፡ {SUPPORT_EMAIL} | ስልክ፡ {SUPPORT_PHONE}"
        )
    }
    return responses.get(intent, responses["general"])

def generate_auto_reply(message: str) -> str:
    """Generate a respectful, bilingual, personalized auto-reply."""
    language = detect_language(message)
    intent = classify_message(message)

    if language == "amharic":
        return amharic_response(intent)
    else:
        eng = english_response(intent)
        amh = amharic_response(intent)
        return f"{eng}\n\n{amh}\n\n— *{HOTEL_NAME} Guest Assist Team*"
