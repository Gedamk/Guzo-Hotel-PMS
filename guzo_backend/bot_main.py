# -*- coding: utf-8 -*-
"""Deprecated Telegram polling entrypoint.

The backend package must not start a separate Telegram long-polling bot.
Use the PostgreSQL/PMS-aligned guest bot instead:

    python -m guzo_booking_bot.modules.message_router
"""


def main():
    print(
        "Deprecated backend bot disabled. "
        "Use: python -m guzo_booking_bot.modules.message_router"
    )


if __name__ == "__main__":
    main()
