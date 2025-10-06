# main.py
import logging
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------
# Bot Handlers
# ----------------------------
async def start(update, context):
    await update.message.reply_text("Welcome! Guzo Booking Bot is now online.")

async def echo(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

# ----------------------------
# Main Function
# ----------------------------
def main():
    # Set timezone to a pytz-supported zone to avoid APScheduler error
    tz = pytz.timezone("Africa/Addis_Ababa")  # adjust your timezone

    # Build Telegram Application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    # Run the bot
    print("Bot started...")
    app.run_polling()

# ----------------------------
# Entry Point
# ----------------------------
if __name__ == "__main__":
    main()
