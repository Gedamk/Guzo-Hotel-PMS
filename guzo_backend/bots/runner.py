# -*- coding: utf-8 -*-
"""Deprecated multi-bot polling runner.

The production phone-friendly Telegram bot for Guzo PMS must run as a single
long-polling process to avoid Telegram 409 Conflict errors:

    python -m guzo_booking_bot.modules.message_router
"""


def main():
    print(
        "Deprecated multi-bot runner disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
