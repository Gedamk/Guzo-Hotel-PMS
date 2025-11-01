# guzo_backend/modules/telegram_bot.py
from guzo_backend.modules.booking_handler import handle_booking

async def handle_message(update):
    message = getattr(update, "message", None)
    if not message:
        return

    data = {
        "Hotel Name": "Demo Hotel",
        "Guest Name": getattr(message, "from_user", "Guest"),
        "Check-in": "2025-09-20",
        "Check-out": "2025-09-21",
        "Room": "101",
        "Source": "Telegram",
    }
    handle_booking(data)

    # Reply to user
    if hasattr(message, "reply_text"):
        message.reply_text("Booking triggered ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")
