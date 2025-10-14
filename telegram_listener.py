# -*- coding: utf-8 -*-
"""
Telegram Listener (Guzo Guest Assist)
-------------------------------------
- Listens for guest messages via Telegram Bot
- Detects hotel name automatically
- Logs to Guest Assist Google Sheet (with multilingual tracking)
- Logs to Notification Log
- Sends notification email via SendGrid
- Replies politely in guest's language (Amharic, Oromo, English)
"""

import os
import datetime as dt
from dotenv import load_dotenv
import gspread
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from fuzzywuzzy import process
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from translate_message import translate_to_english

# ----------- Load environment variables -----------
load_dotenv(r"C:\Users\Gedan\Desktop\Guzo\.env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
HC_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS")
NL_ID = os.getenv("GOOGLE_SHEET_ID_NOTIFICATIONS")
CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SG_API = os.getenv("SENDGRID_API_KEY")

# ----------- Initialize Google Sheets -----------
gc = gspread.service_account(CREDS)
sheet_guest = gc.open_by_key(GA_ID).sheet1
sheet_hotel = gc.open_by_key(HC_ID).sheet1
sheet_notify = gc.open_by_key(NL_ID).sheet1


# ----------- Helper functions -----------
def detect_hotel_name(message, hotel_list):
    """Find closest matching hotel name in a message."""
    if not hotel_list:
        return None
    best, score = process.extractOne(message, hotel_list)
    return best if score > 70 else None


def log_to_sheets(hotel_name, guest_name, original_message, translated_message, lang_code, source="Telegram"):
    """Record booking and log notification with multilingual info."""
    now = dt.datetime.now().isoformat(timespec="seconds")
    sheet_guest.append_row([
        hotel_name,           # Hotel Name
        guest_name,           # Guest Name
        "",                   # Check-in
        "",                   # Check-out
        "",                   # Room
        source,               # Source
        original_message,     # Original Message
        "Pending",            # Status
        now,                  # Timestamp
        translated_message,   # Translated English Text
        lang_code             # Detected Language
    ])

    sheet_notify.append_row([
        dt.date.today().isoformat(),
        hotel_name,
        f"New booking via {source}",
        f"Lang={lang_code}",
        "Logged"
    ])


def notify_manager(hotel_name, guest_name, message_text):
    """Send email notification to hotel manager."""
    hotels = sheet_hotel.get_all_records()
    for h in hotels:
        if h.get("Hotel Name", "").strip().lower() == hotel_name.lower():
            manager_email = h.get("ManagerEmail")
            if manager_email and SG_API:
                sg = SendGridAPIClient(SG_API)
                email = Mail(
                    from_email="reports@guzoassist.com",
                    to_emails=manager_email,
                    subject=f"[Guzo Booking] New Telegram inquiry for {hotel_name}",
                    plain_text_content=(
                        f"Dear {h.get('Manager Name', 'Manager')},\n\n"
                        f"New booking inquiry from {guest_name}.\n\n"
                        f"Message:\n{message_text}\n\n"
                        f"Ã¢ÂÂ Guzo Guest Assist System"
                    ),
                )
                sg.send(email)
                return True
    return False


# ----------- Telegram Bot Handler -----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.strip()
    print(f"Ã°ÂÂÂ© Message from {user.first_name}: {message_text}")

    # Translate to English
    translated, lang_code = translate_to_english(message_text)
    print(f"Ã°ÂÂÂ Detected language: {lang_code} Ã¢ÂÂ Translated: {translated}")

    # Detect hotel name
    hotel_names = [h["Hotel Name"] for h in sheet_hotel.get_all_records() if h.get("Hotel Name")]
    detected_hotel = detect_hotel_name(translated, hotel_names)

    if detected_hotel:
        # Ã¢ÂÂ Log multilingual info
        log_to_sheets(detected_hotel, user.first_name, message_text, translated, lang_code)
        sent = notify_manager(detected_hotel, user.first_name, translated)

        # Reply in guest's own language
        if lang_code == "am":
            response = "Ã¢ÂÂ Ã¡ÂÂµÃ¡ÂÂ Ã¡ÂÂ¦Ã¡ÂÂ³ Ã¡ÂÂÃ¡ÂÂ«Ã¡ÂÂ£Ã¡ÂÂ Ã¡ÂÂ¥Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂ°Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂ¢ Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂ¥Ã¡ÂÂ­Ã¡ÂÂµÃ¡ÂÂ Ã¡ÂÂ°Ã¡ÂÂÃ¡ÂÂ¥Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂ¢"
        elif lang_code in ["om", "omr"]:
            response = "Ã¢ÂÂ Galatoomi! Ergaan keessan ni fudhatame, ni hojjatama."
        else:
            response = f"Ã¢ÂÂ Thank you, {user.first_name}! Your booking request for {detected_hotel} has been received."

        if not sent:
            response += "\nÃ¢ÂÂ Ã¯Â¸Â Manager contact is missing."

        await update.message.reply_text(response)
        print(f"Ã¢ÂÂ Booking processed for {detected_hotel}")
    else:
        await update.message.reply_text(
            "Ã°ÂÂÂ Sorry, I could not detect the hotel name. Please include the hotel name in your message (e.g. 'Hotel A')."
        )


# ----------- Start Bot -----------
def main():
    print("Ã°ÂÂÂ Guzo Guest Assist Telegram bot running with multilingual tracking...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
