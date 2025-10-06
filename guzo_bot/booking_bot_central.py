# booking_bot_central.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import imapclient
import pyzmail
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from twilio.rest import Client as TwilioClient
from flask import Flask, request
import threading
import os
import time

# =======================
# === ENVIRONMENT SETUP ==
# =======================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
YAHOO_EMAIL = os.getenv("YAHOO_EMAIL")
YAHOO_PASSWORD = os.getenv("YAHOO_PASSWORD")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH")
TWILIO_PHONE = "whatsapp:+14155238886"  # Twilio sandbox

# =======================
# === GOOGLE SHEETS SETUP ==
# =======================
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
CREDS_FILE = "guzo_service_account.json"
SHEET_ID = "1hjFpbnORanH44Oi5FNEM_axVBqSL_6UmvozwxEekhMs"

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
client = gspread.authorize(creds)
bookings_ws = client.open_by_key(SHEET_ID).sheet1

# =======================
# === FLASK APP SETUP ===
# =======================
web_app = Flask(__name__)

# =======================
# === TWILIO SETUP ======
# =======================
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# =======================
# === DYNAMIC HOTEL DIRECTORY ===
# =======================
def load_hotels():
    try:
        hotel_tab = client.open_by_key(SHEET_ID).worksheet("Hotels")
        hotels = hotel_tab.get_all_records()
        return hotels
    except gspread.WorksheetNotFound:
        print("❌ 'Hotels' tab not found. Please create it in Google Sheets.")
        return []

hotel_directory = load_hotels()

# Auto-refresh hotels every 5 minutes
def refresh_hotels(interval=300):
    global hotel_directory
    while True:
        hotel_directory = load_hotels()
        time.sleep(interval)

threading.Thread(target=refresh_hotels, daemon=True).start()

def get_hotel_contact(hotel_name):
    for hotel in hotel_directory:
        if hotel["Hotel Name"].lower() == hotel_name.lower():
            return hotel
    return None

# =======================
# === HELPER FUNCTIONS ===
# =======================
def log_booking(hotel_name, name, checkin, checkout, room, source, contact):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bookings_ws.append_row([hotel_name, name, checkin, checkout, room, source, contact, "Pending", timestamp])
    print(f"📩 New booking for {hotel_name} from {source}: {name}, {checkin} → {checkout}, {room}")
    sync_bookings_to_hotel_tab(hotel_name)

def sync_bookings_to_hotel_tab(hotel_name):
    all_bookings = bookings_ws.get_all_records()
    try:
        hotel_tab = client.open_by_key(SHEET_ID).worksheet(hotel_name)
    except gspread.WorksheetNotFound:
        hotel_tab = client.open_by_key(SHEET_ID).add_worksheet(title=hotel_name, rows="100", cols="10")
        hotel_tab.append_row(["Hotel Name", "Guest Name", "Check-in", "Check-out", "Room", "Source", "Contact", "Status", "Timestamp"])
    hotel_tab.resize(rows=1)
    for booking in all_bookings:
        if booking["Hotel Name"].lower() == hotel_name.lower():
            hotel_tab.append_row(list(booking.values()))

# =======================
# === TELEGRAM HANDLERS ===
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Guzo Guest Assist!\n\n"
        "Send your booking as:\nHotel Name, Name, Check-in, Check-out, Room\nExample:\nABAY Hotel, John Doe, 2025-09-20, 2025-09-22, Deluxe"
    )

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guest_message = update.message.text
    try:
        hotel_name, name, checkin, checkout, room = [x.strip() for x in guest_message.split(",")]
        hotel = get_hotel_contact(hotel_name)
        if hotel:
            chat_id = hotel["Telegram Chat ID"]
            await update.message.reply_text(
                f"✅ Booking received for {hotel_name}!\nName: {name}\nCheck-in: {checkin}\nCheck-out: {checkout}\nRoom: {room}"
            )
            log_booking(hotel_name, name, checkin, checkout, room, "Telegram", chat_id)
        else:
            await update.message.reply_text(f"⚠️ Hotel '{hotel_name}' not found in directory.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid format! Use: Hotel Name, Name, Check-in, Check-out, Room")

# =======================
# === EMAIL HANDLER ===
# =======================
async def check_email(imap_server, email_user, email_pass, source_name):
    try:
        mail = imapclient.IMAPClient(imap_server, ssl=True)
        mail.login(email_user, email_pass)
        mail.select_folder('INBOX')
        UIDs = mail.search(['UNSEEN'])
        for uid in UIDs:
            raw_msg = mail.fetch([uid], ['BODY[]', 'FLAGS'])
            msg = pyzmail.PyzMessage.factory(raw_msg[uid][b'BODY[]'])
            text = msg.text_part.get_payload().decode(msg.text_part.charset) if msg.text_part else ""
            try:
                hotel_name, name, checkin, checkout, room = [x.strip() for x in text.split(",")]
                log_booking(hotel_name, name, checkin, checkout, room, source_name, email_user)
            except ValueError:
                print(f"⚠️ Invalid {source_name} email format: {text}")
            mail.add_flags(uid, ['\\Seen'])
        mail.logout()
    except Exception as e:
        print(f"❌ Error checking {source_name}: {e}")

# =======================
# === FLASK ROUTES ===
# =======================
@web_app.route("/booking", methods=["POST"])
def website_booking():
    data = request.json
    hotel_name = data.get("hotel_name")
    name = data.get("name")
    checkin = data.get("checkin")
    checkout = data.get("checkout")
    room = data.get("room")
    contact = data.get("email")
    log_booking(hotel_name, name, checkin, checkout, room, "Website", contact)
    return {"status": "success", "message": "Booking received!"}

@web_app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.values.get("From")
    body = request.values.get("Body")
    try:
        hotel_name, name, checkin, checkout, room = [x.strip() for x in body.split(",")]
        hotel = get_hotel_contact(hotel_name)
        if hotel:
            log_booking(hotel_name, name, checkin, checkout, room, "WhatsApp", from_number)
            twilio_client.messages.create(
                body=f"✅ Booking received for {hotel_name}!\nName: {name}\nCheck-in: {checkin}\nCheck-out: {checkout}\nRoom: {room}",
                from_=TWILIO_PHONE,
                to=from_number
            )
        else:
            twilio_client.messages.create(
                body=f"⚠️ Hotel '{hotel_name}' not found in directory.",
                from_=TWILIO_PHONE,
                to=from_number
            )
    except ValueError:
        twilio_client.messages.create(
            body="⚠️ Invalid format! Send as: Hotel Name, Name, Check-in, Check-out, Room",
            from_=TWILIO_PHONE,
            to=from_number
        )
    return "OK", 200

# =======================
# === MAIN APP RUN ===
# =======================
if __name__ == "__main__":
    # Telegram bot setup
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_message))

    # Job queue for email checks
    job_queue = app.job_queue
    job_queue.run_repeating(lambda ctx: asyncio.run(check_email("imap.mail.yahoo.com", YAHOO_EMAIL, YAHOO_PASSWORD, "Yahoo")), interval=60, first=10)
    job_queue.run_repeating(lambda ctx: asyncio.run(check_email("imap.gmail.com", GMAIL_EMAIL, GMAIL_PASSWORD, "Gmail")), interval=60, first=20)

    # Run Flask in a separate thread
    threading.Thread(target=lambda: web_app.run(port=5000), daemon=True).start()

    # Start Telegram bot
    app.run_polling()


