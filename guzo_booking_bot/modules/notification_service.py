# guzo_booking_bot/modules/notification_service.py
import asyncio
import logging
from guzo_booking_bot.modules import notifications
from guzo_booking_bot.modules.recipient_preferences import recipient_preferences
from guzo_booking_bot.config import ENV

# Setup logging
logging.basicConfig(
    filename="logs/notifications.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def notify_user(user_key, message, subject=""):
    if user_key not in recipient_preferences:
        logging.warning(f"User {user_key} not found in preferences.")
        return

    prefs = recipient_preferences[user_key]
    channels = prefs.get("preferred_channels", [])

    tasks = []
    for channel in channels:
        if channel == "email":
            tasks.append(asyncio.to_thread(notifications.send_email, prefs["email"], subject, message))
        elif channel == "telegram":
            tasks.append(asyncio.to_thread(notifications.send_telegram, prefs["telegram_id"], message))
        elif channel == "whatsapp":
            tasks.append(asyncio.to_thread(notifications.send_whatsapp_sms, prefs["whatsapp"], message))
        elif channel == "viber":
            tasks.append(asyncio.to_thread(notifications.send_viber, prefs["viber_id"], message))
        else:
            logging.warning(f"Unknown channel {channel} for user {user_key}")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            logging.error(f"Notification error for {user_key}: {res}")
        else:
            logging.info(f"Notification sent to {user_key} successfully via {channels}")

