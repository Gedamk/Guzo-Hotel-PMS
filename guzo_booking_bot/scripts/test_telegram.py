from guzo_booking_bot.modules import telegram_service

def main():
    chat_id = input("Enter target chat_id: ").strip()
    if not chat_id:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ No chat_id entered. Cancelled.")
        return

    msg = "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Test from Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telegram notifications working!"
    ok, resp = telegram_service.send_message(chat_id, msg)

    print("ok:", ok)
    print("resp:", resp)

if __name__ == "__main__":
    main()
