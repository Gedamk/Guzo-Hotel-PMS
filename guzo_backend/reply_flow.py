# -*- coding: utf-8 -*-
"""
reply_flow.py – Smart Bilingual Auto-Reply Engine (v7.1)
--------------------------------------------------------
Core conversational engine for Guzo Guest Assist.
Blends Ethiopian warmth with global hotel professionalism.

✨ Key Features:
• Detects Amharic or English automatically
• Classifies messages (booking, pricing, cancellation, etc.)
• Logs new client requests to Google Sheets
• Prevents duplicate logging
• Auto-sends Telegram + Email confirmations
• Fetches live hotel data from Google Sheets
"""

import re
from datetime import datetime
from guzo_backend.modules import google_sheets
from guzo_backend.modules.auto_confirmation import confirm_request
from guzo_backend.utils.hotel_directory import fetch_hotel_data

# ======================================================
# MAIN PROCESSOR
# ======================================================

async def process_message(update, context):
    """
    Entry point called by message_router.py.
    Detects language, intent, logs request, confirms if new.
    """
    message = update.message.text.strip()
    user = update.effective_user
    guest_name = user.first_name or "Guest"

    # Detect intent & language
    language = detect_language(message)
    intent = classify_message(message)
    hotel_name = detect_hotel_name(message)

    # Handle hotel-specific query
    if hotel_name:
        reply = generate_hotel_reply(hotel_name, language)
        await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # Handle booking flow
    if intent == "booking":
        hotel = hotel_name or "Unspecified Hotel"
        existing = google_sheets.find_existing_request(guest_name, message)

        if existing:
            reply = (
                "✅ Your previous request is already being processed.\n"
                "Our Guzo team will follow up soon."
                if language == "english" else
                "✅ ጥያቄዎ ቀድሞውኑ ተቀባ እና በሂደት ላይ ነው።"
            )
            await update.message.reply_text(reply)
            return

        # Log new booking request
        google_sheets.log_new_request(guest_name, hotel, message)
        await confirm_request(update, context, hotel, message)
        return

    # Otherwise — general or greeting
    if language == "amharic":
        reply = amharic_response(intent)
    else:
        reply = bilingual_response(intent)

    await update.message.reply_text(reply, parse_mode="Markdown")


# ======================================================
# DETECTION HELPERS
# ======================================================

def detect_language(text: str) -> str:
    """Detect if message is in Amharic or English."""
    amharic_pattern = re.compile(r'[\u1200-\u137F]')
    return "amharic" if amharic_pattern.search(text) else "english"


def classify_message(text: str) -> str:
    """Detect guest intent from message keywords."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["book", "reserve", "room", "night", "stay"]):
        return "booking"
    elif any(w in text_lower for w in ["cancel", "change", "modify"]):
        return "cancellation"
    elif any(w in text_lower for w in ["thank", "thanks", "appreciate"]):
        return "gratitude"
    elif any(w in text_lower for w in ["price", "rate", "cost", "offer"]):
        return "pricing"
    elif any(w in text_lower for w in ["hello", "hi", "good morning", "good evening", "selam"]):
        return "greeting"
    else:
        return "general"


def detect_hotel_name(text: str) -> str:
    """Try to identify hotel name mentioned by guest."""
    try:
        df = google_sheets.load_hotel_contacts()
        df["Hotel Name Lower"] = df["Hotel Name"].str.lower()
        text_lower = text.lower()
        match = df[df["Hotel Name Lower"].apply(lambda n: n in text_lower)]
        if not match.empty:
            return match.iloc[0]["Hotel Name"]
    except Exception:
        pass
    return None


# ======================================================
# RESPONSE GENERATORS
# ======================================================

def english_response(intent: str) -> str:
    """Professional English replies."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    responses = {
        "greeting": "👋 Hello! Thank you for contacting *Guzo Guest Assist*.\nHow may we help you today?",
        "booking": f"🛎️ Thank you for your booking request.\nOur reservation team will confirm your stay shortly.\n📅 Date: {today}",
        "cancellation": "We’re sorry to hear you wish to cancel. Please share your reservation ID or hotel name so we can assist.",
        "pricing": "💰 We’ll send you available rates and offers soon. Could you please share your travel dates?",
        "gratitude": "You're most welcome! It’s always our pleasure to serve you. 😊",
        "general": "Thank you for reaching out to *Guzo Guest Assist*. A front-desk representative will reply shortly."
    }
    return responses.get(intent, responses["general"])


def amharic_response(intent: str) -> str:
    """Polite Amharic responses for Ethiopian guests."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    responses = {
        "greeting": "👋 ሰላም! እንኳን ወደ ጉዞ ጌስት አሲስት በደህና መጡ። እንዴት እንርዳዎታለን?",
        "booking": f"🛎️ ስለ ቦታ መያዝዎ እናመሰግናለን። ቦታዎ በቅርቡ ይረጋገጣል።\n📅 ቀን፡ {today}",
        "cancellation": "ስለ መሰረዝ መጠየቅዎ እናዝናለን። እባኮትን የመያዣዎን መለያ ያስገቡ።",
        "pricing": "የአሁኑ ዋጋና የቅናሽ መረጃዎች በቅርቡ ይላካሉ። እባኮትን የመኖሪያዎን ቀን ያስገቡ።",
        "gratitude": "እኛም እናመሰግናለን። በሁሉም ጊዜ እንገልጻለን።",
        "general": "ስለ መግኘትዎ እናመሰግናለን። በቅርቡ ባለሙያችን ይመልስዎታል።"
    }
    return responses.get(intent, responses["general"])


def bilingual_response(intent: str) -> str:
    """Mix English + Amharic for inclusivity."""
    eng = english_response(intent)
    amh = amharic_response(intent)
    return f"{eng}\n\n{amh}\n\n— *Guzo Guest Assist Team*"


# ======================================================
# HOTEL INFO GENERATOR
# ======================================================

def generate_hotel_reply(hotel_name: str, language: str = "english") -> str:
    """Build friendly bilingual hotel information response."""
    try:
        hotel = fetch_hotel_data(hotel_name)
        if not hotel:
            return "⚠️ Sorry, I couldn’t find details about that hotel."

        city = hotel.get("City", "Ethiopia")
        description = hotel.get("Description", "A beautiful property offering comfortable rooms.")
        services = hotel.get("Services", "Rooms, Restaurant, Wi-Fi, Lounge")
        phone = hotel.get("Phone", "N/A")
        email = hotel.get("Email", "N/A")

        eng = (
            f"🏨 *{hotel_name}* — located in {city}.\n"
            f"{description}\n\n"
            f"**Services:** {services}\n"
            f"📞 {phone}\n📧 {email}\n\n"
            "Would you like to book a stay here?"
        )

        amh = (
            f"🏨 *{hotel_name}* — በ{city} ያለ ቆንጆ ሆቴል ነው።\n"
            f"{description}\n\n"
            f"**አገልግሎቶች:** {services}\n"
            f"📞 {phone}\n📧 {email}\n\n"
            "እባኮትን እዚህ ቦታ መያዣ ማድረግ ትፈልጋለህ?"
        )

        if language == "amharic":
            return amh
        return f"{eng}\n\n{amh}\n\n— *Guzo Guest Assist*"

    except Exception as e:
        return f"⚠️ Could not retrieve hotel data. ({e})"
