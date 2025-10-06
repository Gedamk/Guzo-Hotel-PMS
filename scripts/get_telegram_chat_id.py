# scripts/get_telegram_chat_id.py
from guzo_booking_bot.modules import telegram_service

ids = telegram_service.get_chat_ids_from_updates()

if ids:
    print(f"✅ Found chat IDs: {ids}")
else:
    print("❌ No chat IDs found.")
    print("Steps:")
    print("  1) Open Telegram and send /start to your bot.")
    print("  2) Re-run this script to see the chat id.")
