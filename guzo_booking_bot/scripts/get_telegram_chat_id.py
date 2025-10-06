# scripts/get_telegram_chat_id.py
import requests
from guzo_booking_bot import config as cfg

def get_chat_ids_from_updates():
    url = f"https://api.telegram.org/bot{cfg.TELEGRAM_TOKEN}/getUpdates"
    resp = requests.get(url).json()

    if not resp.get("ok"):
        print("❌ Error fetching updates:", resp)
        return []

    ids = []
    for update in resp.get("result", []):
        if "message" in update and "chat" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            ids.append(chat_id)

    return ids

if __name__ == "__main__":
    ids = get_chat_ids_from_updates()
    if ids:
        print("✅ Found chat IDs:", ids)
    else:
        print("❌ No chat IDs found. Send /start to your bot in Telegram and re-run.")
