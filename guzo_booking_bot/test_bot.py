# -*- coding: utf-8 -*-
"""Deprecated Telegram polling entrypoint.

Production Telegram communication for Guzo PMS runs only through:

    python -m guzo_booking_bot.modules.message_router

This file intentionally does not start Telegram polling. Keeping multiple
pollers for the same token causes Telegram 409 Conflict errors and unstable
phone conversations.
"""


def main():
    print(
        "Deprecated test bot disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
