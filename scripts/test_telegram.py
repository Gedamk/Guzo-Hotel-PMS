# scripts/test_telegram.py
from guzo_booking_bot.modules import telegram_service
from guzo_booking_bot import config as cfg

def main():
    chat_id = cfg.TELEGRAM_CHAT_ID
    if not chat_id:
        ids = telegram_service.get_chat_ids_from_updates()
        if ids:
            chat_id = ids[0]
            print(f"Ã¢ÂÂ Using fetched chat_id: {chat_id}")
        else:
            print("Ã¢ÂÂ No chat_id found. Send /start to your bot and retry.")
            return

    try:
        resp = telegram_service.send_message(
            chat_id=chat_id,
            text="Ã¢ÂÂ Test from Guzo Guest Assist Ã¢ÂÂ Telegram notifications working!"
        )
        print("ok:", True)
        print("resp:", resp)
    except Exception as e:
        print("Telegram send failed:", e)
        print("ok:", False)
        print("resp:", None)

if __name__ == "__main__":
    main()

