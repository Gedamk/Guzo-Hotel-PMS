# -*- coding: utf-8 -*-
"""
Reply Engine
Determines the correct automated reply to a guest message.
"""

def generate_reply(text: str) -> str:
    text_lower = text.lower().strip()

    # --- Simple rule-based logic ---
    if "booking" in text_lower or "reserve" in text_lower:
        return "Thank you! Your booking request has been received. Our team will confirm shortly."

    if "airport" in text_lower or "pickup" in text_lower:
        return "Airport pickup request noted. Our driver will contact you soon."

    if "price" in text_lower or "rate" in text_lower:
        return "Please specify your travel dates so we can provide the correct room rate."

    if "hello" in text_lower or "hi" in text_lower:
        return "Hello! Welcome to Guzo Guest Assist. How may we help you today?"

    if "wifi" in text_lower or "internet" in text_lower:
        return "Please check your Wi-Fi connection. If issues persist, contact reception."

    # --- Default fallback ---
    return "Thank you for contacting us. Our team will get back to you soon."

