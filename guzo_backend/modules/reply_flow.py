# -*- coding: utf-8 -*-
"""
reply_flow.py – fallback language + intent utilities for Guzo Guest Assist
If the advanced NLP module is missing, this provides basic detection.
"""

from langdetect import detect

def detect_language(text: str) -> str:
    """Try to detect if text is Amharic or English."""
    try:
        lang = detect(text)
    except Exception:
        lang = "en"
    return lang

def classify_message(text: str) -> str:
    """Simple classification by keywords."""
    msg = text.lower()
    if any(w in msg for w in ["book", "room", "stay", "reserve", "check-in", "booking", "መያዣ"]):
        return "booking"
    if any(w in msg for w in ["cancel", "change", "modify", "reschedule", "refund", "መሰረዝ", "መቀየር"]):
        return "cancellation"
    return "general"
