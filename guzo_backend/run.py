# -*- coding: utf-8 -*-
"""Deprecated Telegram polling launcher.

Do not start a Telegram bot from ``guzo_backend``. Backend service startup is
handled by Uvicorn, and the single Telegram bot entrypoint is:

    python -m guzo_booking_bot.modules.message_router
"""


def main():
    print(
        "Deprecated backend run launcher disabled. "
        "Use Uvicorn for the API and message_router for Telegram."
    )


if __name__ == "__main__":
    main()
