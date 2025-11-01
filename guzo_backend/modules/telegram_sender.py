# -*- coding: utf-8 -*-
"""
Telegram Sender Module
Handles sending messages to managers via Telegram Bot API.
Used for alerts (escalations, special offers, occupancy trends, etc.)
"""

import requests
from guzo_backend import config


def send_message(message, chat_id=None, parse_mode="Markdown"):
    """
    Send a Telegram message to a chat.

    Args:
        message (str): The text message to send
        chat_id (str): Telegram chat ID (optional, falls back to .env config)
        parse_mode (str): "Markdown" or "HTML" for rich formatting
    """
    token = config.TELEGRAM_TOKEN
    chat_id = chat_id or config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Telegram not configured: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return None

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram sent to {chat_id}")
            return resp.json()
        else:
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram API error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram send_message failed: {e}")
        return None


def send_alert(title, body, lang="en"):
    """
    Send a structured alert with multilingual support.
    Useful for manager notifications.
    """
    msg = (
        f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ *{title}*\n\n"
        f"{body}\n\n"
        "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¬ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ English: Alert sent.\n"
        "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂªÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ: ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ³ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ« ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ³ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢\n"
        "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¿ Afaan Oromoo: Beeksisa ergameera."
    )
    return send_message(msg, parse_mode="Markdown")


# =========================================================
# Backward Compatibility Wrapper
# =========================================================
def send_telegram_message(message, chat_id=None, parse_mode="Markdown"):
    """
    Wrapper for backward compatibility.
    Redirects to send_message() so older scripts won't break.
    """
    return send_message(message, chat_id=chat_id, parse_mode=parse_mode)
