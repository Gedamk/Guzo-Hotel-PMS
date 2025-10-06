# scripts/send_test_email.py

import logging
from guzo_booking_bot.modules import notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    to_email = input("Enter test recipient email: ").strip()
    phone = input("Enter test recipient phone (with +countrycode, optional): ").strip()

    subject = "Guzo Booking Bot - Test Notification"
    message = (
        "Hello! 👋\n\n"
        "This is a multi-channel test from your Guzo Booking Bot.\n"
        "If one channel fails, the system will automatically try the next.\n"
        "✅ Powered by Guzo Guest Assist."
    )

    results = notifications.send_notification_multi(
        to_email=to_email,
        subject=subject,
        body=message,
        phone=phone if phone else None
    )

    print("\n--- Notification Results ---")
    for channel, success in results.items():
        print(f"{channel.upper():10}: {'✅ SUCCESS' if success else '❌ FAILED'}")
