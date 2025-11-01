# guzo_booking_bot/modules/telegram_service.py
import requests
from guzo_booking_bot import config as cfg

BASE_URL = f"https://api.telegram.org/bot{cfg.TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    return r.json()
