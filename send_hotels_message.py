# send_hotels_message.py
from guzo_booking_bot.modules.google_sheets import get_hotel_contacts
from guzo_booking_bot.modules.messaging import (
    send_whatsapp_message, send_email_message, send_telegram_message, send_viber_message
)
from guzo_booking_bot.modules.utils import validate_phone_number

def main():
    hotels = get_hotel_contacts()
    for hotel in hotels:
        name = hotel['hotel_name']
        number = validate_phone_number(hotel.get('contact'))
        email = hotel.get('email')
        telegram = hotel.get('telegram')

        message = f"Hello {name},\n\nWe are reaching out from Guzo Guest Assist.\n" \
                  "We provide professional guest service support to enhance your hotel operations.\n\n" \
                  "Best regards,\nGuzo Guest Assist Team"

        if number:
            send_whatsapp_message(number, message)
            send_viber_message(number, message)
        if email:
            send_email_message(email, message)
        if telegram:
            send_telegram_message(telegram, message)

if __name__ == "__main__":
    main()
