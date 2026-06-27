# -*- coding: utf-8 -*-
"""Deprecated Telegram polling entrypoint.

This legacy Google-Sheets-era booking bot is disabled. The active Guzo PMS
Telegram bot writes through the FastAPI/PostgreSQL backend:

    python -m guzo_booking_bot.modules.message_router
"""


def main():
    print(
        "Deprecated conversational booking bot disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
