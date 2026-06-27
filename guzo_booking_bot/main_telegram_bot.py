# -*- coding: utf-8 -*-
"""Deprecated Telegram polling entrypoint.

The supported Guzo PMS Telegram bot is:

    python -m guzo_booking_bot.modules.message_router

This module is kept as a compatibility notice only. It does not start polling,
so it cannot compete with the production bot or create Telegram 409 Conflict
errors.
"""


def main():
    print(
        "Deprecated launcher disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
