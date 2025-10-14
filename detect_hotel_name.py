# -*- coding: utf-8 -*-
"""
Hotel Name Detector
Uses fuzzy string matching to find hotel name in multi-language messages.
"""

import re
from fuzzywuzzy import process

def detect_hotel_name(message: str, hotel_list: list):
    """
    Detects the hotel name mentioned in a message.
    Supports Amharic + English mixed text.
    """
    # Normalize text (remove punctuation, extra spaces)
    clean = re.sub(r'[^\w\s]', ' ', message).strip().lower()
    
    # Try exact substring matches first
    for h in hotel_list:
        if h.lower() in clean:
            return h

    # Fallback: fuzzy matching (best partial ratio)
    best_match, score = process.extractOne(clean, hotel_list, scorer=None)
    return best_match if score > 80 else None
