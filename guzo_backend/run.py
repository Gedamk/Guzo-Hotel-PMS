import threading
import asyncio
from modules.telegram_bot import run_telegram_bot
from modules.flask_app import web_app
from modules.email_handler import check_email
from config import GMAIL_EMAIL, GMAIL_PASSWORD, YAHOO_EMAIL, YAHOO_PASSWORD

if __name__ == "__main__":
    # Start Flask in background
    threading.Thread(target=lambda: web_app.run(port=5000), daemon=True).start()

    # Start Telegram bot
    app = run_telegram_bot()

    # Schedule email checks
    job_queue = app.job_queue
    job_queue.run_repeating(lambda ctx: asyncio.run(check_email("imap.mail.yahoo.com", YAHOO_EMAIL, YAHOO_PASSWORD, "Yahoo")), interval=60, first=10)
    job_queue.run_repeating(lambda ctx: asyncio.run(check_email("imap.gmail.com", GMAIL_EMAIL, GMAIL_PASSWORD, "Gmail")), interval=60, first=20)

    # Start polling
    app.run_polling()
