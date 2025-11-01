# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Chat Logger (v4.0)
-------------------------------------------------
Unified chat logger for hotel managers and guests.

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Maps Telegram users to hotel properties
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Logs every incoming message for reporting & dashboards
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Integrates seamlessly with report_notifier and Streamlit dashboards
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Built for secure, scalable multi-property hospitality automation
"""

import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

# ============================================================
# File Path Configuration
# ============================================================
STORAGE_DIR = os.path.join(os.getcwd(), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

CHAT_LOG_PATH = os.path.join(STORAGE_DIR, "chat_ids.json")
MESSAGE_LOG_PATH = os.path.join(STORAGE_DIR, "message_log.json")

# ============================================================
# Property Directory (expandable as hotels onboard)
# ============================================================
PROPERTY_MAP = {
    "Kaku": "Zoma Hotel",
    "Mamo": "Hyatt Regency",
    "Sara": "Hilton Addis",
    "Rafaela": "Skylight Hotel",
}

# ============================================================
# Utility Functions
# ============================================================
def load_json(path: str):
    """Safely load JSON data from disk."""
    if not os.path.exists(path):
        return {} if "chat" in path else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Corrupted JSON at {path}, resetting...")
        return {} if "chat" in path else []

def save_json(path: str, data):
    """Save dictionary or list to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================
# Chat ID Registration Function
# ============================================================
async def log_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Register or confirm Telegram user connection to property.
    Called automatically when user sends first message.
    """
    user = update.message.from_user
    chat_id = str(update.message.chat_id)
    name = user.first_name or "Guest"
    username = user.username or "N/A"
    language = user.language_code or "unknown"

    data = load_json(CHAT_LOG_PATH)

    if chat_id not in data:
        property_name = PROPERTY_MAP.get(name, "Unassigned Property")

        data[chat_id] = {
            "name": name,
            "username": username,
            "property": property_name,
            "chat_id": chat_id,
            "language": language,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "email": f"{name.lower()}@guzoassist.com" if property_name != "Unassigned Property" else "",
            "active": True,
        }

        save_json(CHAT_LOG_PATH, data)
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Registered {name} ({chat_id}) ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {property_name}")

        await update.message.reply_text(
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Hello {name}!\n"
            f"You are now connected to *Guzo Guest Assist*.\n\n"
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¨ Property: *{property_name}*\n"
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Registered: {data[chat_id]['registered_at']}\n"
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Language: {language.upper()}",
            parse_mode="Markdown"
        )
    else:
        user_data = data[chat_id]
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Returning user detected: {user_data['name']} ({chat_id})")
        await update.message.reply_text(
            f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Welcome back, {name}!\n"
            f"Your connection with *{user_data['property']}* is active.\n"
            f"Messages are now synced automatically. ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ",
            parse_mode="Markdown"
        )

# ============================================================
# Message Logging Function (for Dashboard)
# ============================================================
async def log_message_to_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Log all user messages to message_log.json
    (used by the dashboard feed and reporting modules).
    """
    user = update.message.from_user
    chat_id = str(update.message.chat_id)
    message_text = update.message.text.strip()

    log_entry = {
        "chat_id": chat_id,
        "user_name": user.first_name or "Guest",
        "message": message_text,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    logs = load_json(MESSAGE_LOG_PATH)
    if not isinstance(logs, list):
        logs = []

    logs.append(log_entry)
    save_json(MESSAGE_LOG_PATH, logs)

    print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Message logged from {log_entry['user_name']}: {log_entry['message']}")

    # Optionally reply instantly for feedback
    await update.message.reply_text(
        f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¬ Message received: *{message_text}*\n"
        f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Logged successfully for property reporting.",
        parse_mode="Markdown"
    )
