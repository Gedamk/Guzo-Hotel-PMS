# -*- coding: utf-8 -*-
"""
Inbound Email Handler – Guzo Guest Assist (v4)
------------------------------------------------
Handles inbound booking emails, logs them to Google Sheets,
sends bilingual (Amharic + English) confirmations with PDF receipts,
and notifies hotel managers on Telegram.
"""

import os, sys, json, re, io, base64, telegram, asyncio
from datetime import datetime
from email import message_from_string
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------------------------------------------
# ✅ FIXED: Reliable root path detection for imports
# -------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Now safe to import internal modules
from guzo_booking_bot.modules import google_sheets, log_helper

# -------------------------------------------------------
# ENVIRONMENT VARIABLES
# -------------------------------------------------------
load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "bookings@guzoassist.com")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# -------------------------------------------------------
# LOAD HOTEL CONFIGURATION
# -------------------------------------------------------
CONFIG_PATH = os.path.join(ROOT_DIR, "hotels_config.json")
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"❌ hotels_config.json not found at {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    HOTEL_DATA = json.load(f)["HOTELS"]

# -------------------------------------------------------
# FIND HOTEL BY EMAIL
# -------------------------------------------------------
def find_hotel_by_email(to_email: str):
    for h in HOTEL_DATA:
        if h["email"].lower() == to_email.lower():
            return h
    return None

# -------------------------------------------------------
# PARSE BOOKING EMAIL
# -------------------------------------------------------
def parse_booking_email(email_raw: str):
    msg = message_from_string(email_raw)
    sender = msg.get("From", "")
    to = msg.get("To", "")
    subject = msg.get("Subject", "")
    payload = msg.get_payload()

    # Handle plain or multipart email bodies
    if isinstance(payload, list):
        body = ""
        for part in payload:
            try:
                body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                pass
    else:
        try:
            body = payload.decode("utf-8", errors="ignore")
        except AttributeError:
            body = str(payload)

    guest_name = re.search(r"Name[:\- ]+([A-Za-z ]+)", body)
    checkin = re.search(r"Check-?in[:\- ]+([\d-]+)", body)
    nights = re.search(r"Nights[:\- ]+(\d+)", body)
    room = re.search(r"Room[:\- ]+([A-Za-z ]+)", body)
    rate = re.search(r"Rate[:\- ]+([\d,]+)", body)

    return {
        "sender": sender,
        "to": to,
        "subject": subject,
        "guest_name": guest_name.group(1).strip() if guest_name else "Unknown",
        "checkin": checkin.group(1).strip() if checkin else "Unknown",
        "nights": nights.group(1).strip() if nights else "1",
        "room": room.group(1).strip() if room else "Standard",
        "rate": rate.group(1).strip() if rate else "0",
        "body": body.strip(),
    }

# -------------------------------------------------------
# APPEND BOOKING TO GOOGLE SHEET
# -------------------------------------------------------
def append_booking_to_sheet(hotel, booking):
    sheet = google_sheets._open_sheet(hotel["sheet_id"], "Bookings")
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        booking["guest_name"],
        booking["checkin"],
        booking["nights"],
        booking["room"],
        booking["rate"],
        booking["sender"],
        "Pending Confirmation",
    ]
    sheet.append_row(row)
    log_helper.log_event("inbound_email_handler", "OK",
                         f"✅ Booking added for {booking['guest_name']} at {hotel['name']}")

# -------------------------------------------------------
# GENERATE BILINGUAL PDF RECEIPT (with logo + confirmation code)
# -------------------------------------------------------
def generate_bilingual_receipt(booking, hotel):
    """Create bilingual (Amharic + English) PDF booking receipt
    with logo, confirmation number, and auto-save to /reports folder.
    """
    font_path = os.path.join("assets", "fonts", "AbyssinicaSIL-Regular.ttf")
    pdfmetrics.registerFont(TTFont("AbyssinicaSIL", font_path))

    reports_dir = os.path.join(ROOT_DIR, "reports", hotel["name"].replace(" ", "_"))
    os.makedirs(reports_dir, exist_ok=True)

    # Generate confirmation code
    date_part = datetime.now().strftime("%Y%m%d")
    initials = "".join([w[0].upper() for w in booking["guest_name"].split() if w])
    confirm_code = f"{hotel['name'].split()[0].upper()}-{date_part}-{initials}{str(hash(booking['guest_name']))[-3:]}"

    filename = f"{confirm_code}.pdf"
    pdf_path = os.path.join(reports_dir, filename)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("AbyssinicaSIL", 13)

    # --- Logo ---
    logo_path = os.path.join("assets", "images", "guzo_logo.png")
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 60, 770, width=70, height=70, preserveAspectRatio=True)

    # --- Header ---
    c.drawString(150, 820, "Guzo Guest Assist – Booking Confirmation")
    c.drawString(150, 800, "የቆይታ ማረጋገጫ (Bilingual Receipt)")
    c.line(60, 790, 530, 790)

    y = 760
    details = [
        f"Confirmation No: {confirm_code}",
        f"Hotel: {hotel['name']}",
        f"Guest: {booking['guest_name']}",
        f"Check-In: {booking['checkin']}",
        f"Nights: {booking['nights']}",
        f"Room Type: {booking['room']}",
        f"Rate: {booking['rate']} ETB",
        "",
        "የመመዝገብ ጥያቄዎ ተቀባይነት አግኝቷል።",
        "እናመሰግናለን ስለ መምረጥዎ Guzo Guest Assist።",
        "",
        "ቆይታዎን እንረዳለን። — Your Stay, Our Assist.",
    ]

    for line in details:
        c.drawString(80, y, line)
        y -= 22

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    with open(pdf_path, "wb") as f:
        f.write(pdf)

    log_helper.log_event("pdf_receipt", "OK",
                         f"🧾 PDF generated for {booking['guest_name']} ({confirm_code}) at {hotel['name']}")
    return pdf, pdf_path, confirm_code

# -------------------------------------------------------
# SEND EMAILS WITH PDF ATTACHMENT
# -------------------------------------------------------
def send_auto_replies(booking, hotel, pdf_bytes, confirm_code):
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    guest_email = re.search(r"<(.+?)>", booking["sender"])
    guest_email = guest_email.group(1) if guest_email else booking["sender"]

    encoded = base64.b64encode(pdf_bytes).decode()
    attach = Attachment(
        file_content=encoded,
        file_type="application/pdf",
        file_name="Guzo_Booking_Confirmation.pdf",
        disposition="attachment",
    )

    guest_mail = Mail(
        from_email=FROM_EMAIL,
        to_emails=guest_email,
        subject=f"Booking Confirmation – {hotel['name']} ({confirm_code})",
        html_content=f"""
        <p>Dear {booking['guest_name']},</p>
        <p>Thank you for booking at <strong>{hotel['name']}</strong>.</p>
        <p>Attached is your bilingual (Amharic + English) confirmation receipt.</p>
        <hr><p><em>ቆይታዎን እንረዳለን። — Your Stay, Our Assist.</em></p>
        """,
    )
    guest_mail.attachment = attach
    sg.send(guest_mail)

    owner_mail = Mail(
        from_email=FROM_EMAIL,
        to_emails=hotel["email"],
        subject=f"New Booking – {hotel['name']} ({confirm_code})",
        html_content=f"""
        <p>📩 New booking received from <strong>{booking['guest_name']}</strong>.</p>
        <ul>
            <li>Check-In: {booking['checkin']}</li>
            <li>Nights: {booking['nights']}</li>
            <li>Room: {booking['room']}</li>
            <li>Rate: {booking['rate']} ETB</li>
            <li>Confirmation No: {confirm_code}</li>
        </ul>
        <p>Automatically logged to your Google Sheet.</p>
        """,
    )
    sg.send(owner_mail)
    log_helper.log_event("auto_reply", "OK",
                         f"📤 PDF receipt ({confirm_code}) sent to {booking['guest_name']}")

# -------------------------------------------------------
# TELEGRAM NOTIFICATION
# -------------------------------------------------------
def notify_hotel_telegram(hotel, booking):
    if not TELEGRAM_TOKEN:
        return
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        msg = (f"🏨 *New Booking Alert – {hotel['name']}*\n"
               f"👤 Guest: {booking['guest_name']}\n"
               f"📅 Check-in: {booking['checkin']}\n"
               f"🛏 Nights: {booking['nights']}\n"
               f"💰 Rate: {booking['rate']} ETB")
        asyncio.run(bot.send_message(chat_id=hotel["telegram_chat_id"], text=msg, parse_mode="Markdown"))
        log_helper.log_event("telegram_notify", "OK", f"📨 Telegram alert sent to {hotel['name']}")
    except Exception as e:
        log_helper.log_event("telegram_notify", "ERROR", f"⚠️ Telegram failed: {e}")

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    SAMPLE_EMAIL_FILE = os.path.join(ROOT_DIR, "backend", "sample_email.txt")
    if not os.path.exists(SAMPLE_EMAIL_FILE):
        print("❌ Missing backend/sample_email.txt")
        sys.exit(1)

    raw_email = open(SAMPLE_EMAIL_FILE, "r", encoding="utf-8").read()
    booking = parse_booking_email(raw_email)
    hotel = find_hotel_by_email(booking["to"])

    if hotel:
        append_booking_to_sheet(hotel, booking)
        pdf, pdf_path, confirm_code = generate_bilingual_receipt(booking, hotel)
        send_auto_replies(booking, hotel, pdf, confirm_code)
        notify_hotel_telegram(hotel, booking)
        print(f"✅ Booking processed with PDF [{confirm_code}] and Telegram alert.")
    else:
        log_helper.log_event("inbound_email_handler", "ERROR", f"No hotel match for {booking['to']}")
        print(f"❌ No hotel match for email: {booking['to']}")
