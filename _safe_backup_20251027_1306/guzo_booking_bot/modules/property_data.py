# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Property Data Utility (v1.0)
--------------------------------------------------
Reads registered Telegram chat IDs and hotel property mappings.
Used by dashboard, report generators, and automation modules.
"""

import json
import os

CHAT_LOG_PATH = os.path.join("storage", "chat_ids.json")

def load_properties():
    """Return all registered properties with chat and manager info."""
    if not os.path.exists(CHAT_LOG_PATH):
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No chat_ids.json found ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ no registered hotels.")
        return []

    try:
        with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ chat_ids.json file is corrupted.")
        return []

    hotels = []
    for chat_id, info in data.items():
        hotels.append({
            "name": info.get("name", "Unknown"),
            "username": info.get("username", ""),
            "property": info.get("property", "Unassigned Property"),
            "chat_id": chat_id,
        })
    return hotels


def get_property_by_chat(chat_id):
    """Return property details for a specific chat_id."""
    if not os.path.exists(CHAT_LOG_PATH):
        return None
    with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(str(chat_id))
