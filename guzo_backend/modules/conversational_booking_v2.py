# -*- coding: utf-8 -*-
"""Deprecated Telegram polling entrypoint.

Use the PostgreSQL/PMS-aligned Telegram bot:

    python -m guzo_booking_bot.modules.message_router
"""


def main():
    print(
        "Deprecated backend conversational bot disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
