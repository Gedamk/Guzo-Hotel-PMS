# receive_booking_message.py
import datetime as dt
import os
from dotenv import load_dotenv
import gspread
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- Load environment (.env) variables ---
load_dotenv(r"C:\Users\Gedan\Desktop\Guzo\.env")

creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
HC_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS")
NL_ID = os.getenv("GOOGLE_SHEET_ID_NOTIFICATIONS")
SG_API = os.getenv("SENDGRID_API_KEY")

gc = gspread.service_account(creds)

sheet_guest = gc.open_by_key(GA_ID).sheet1
sheet_hotel = gc.open_by_key(HC_ID).sheet1
sheet_notify = gc.open_by_key(NL_ID).sheet1

# --- Example incoming booking message ---
incoming_message = {
    "hotel": "Hotel A",
    "guest_name": "Hanna Bekele",
    "language": "am",
    "message": "Ã¡ÂÂ¥Ã¡ÂÂ£Ã¡ÂÂ­Ã¡ÂÂÃ¡ÂÂ Ã¡ÂÂ­Ã¡ÂÂÃ¡ÂÂ Ã¡ÂÂ Ã¡ÂÂÃ¡ÂÂµ Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂµ Ã¡ÂÂÃ¡ÂÂ½Ã¡ÂÂµ Ã¡ÂÂ¥Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂ¢",
    "checkin": "2025-10-12",
    "checkout": "2025-10-14",
    "room": 1,
    "source": "Telegram",
    "revenue": 3800,
}

now = dt.datetime.now().isoformat(timespec="seconds")

# --- Add to Guest Assist sheet ---
sheet_guest.append_row([
    incoming_message["hotel"],
    incoming_message["guest_name"],
    incoming_message["checkin"],
    incoming_message["checkout"],
    incoming_message["room"],
    incoming_message["source"],
    incoming_message["revenue"],
    "Pending",
    now,
])
print("Ã¢ÂÂ Booking recorded in Guest Assist sheet.")

# --- Log to Notification Log ---
sheet_notify.append_row([
    dt.date.today().isoformat(),
    incoming_message["hotel"],
    f"New booking from {incoming_message['guest_name']} via {incoming_message['source']}",
    "Logged",
])
print("Ã°ÂÂÂÃ¯Â¸Â Notification Log updated.")

# --- Find manager email ---
hotels = sheet_hotel.get_all_records()
manager_email = None
for h in hotels:
    if h["Hotel Name"].strip().lower() == incoming_message["hotel"].strip().lower():
        manager_email = h["ManagerEmail"]
        break

if not manager_email:
    print("Ã¢ÂÂ Ã¯Â¸Â No manager email found for hotel.")
else:
    sg = SendGridAPIClient(SG_API)
    subject = f"[Guzo Booking] New guest from {incoming_message['source']}"
    body = (
        f"Dear Manager,\n\n"
        f"You have a new booking at {incoming_message['hotel']}.\n\n"
        f"Guest: {incoming_message['guest_name']}\n"
        f"Check-in: {incoming_message['checkin']}\n"
        f"Check-out: {incoming_message['checkout']}\n"
        f"Room(s): {incoming_message['room']}\n"
        f"Source: {incoming_message['source']}\n"
        f"Revenue: {incoming_message['revenue']} ETB\n\n"
        f"Ã¢ÂÂ Guzo Guest Assist System"
    )

    message = Mail(
        from_email="reports@guzoassist.com",
        to_emails=manager_email,
        subject=subject,
        plain_text_content=body,
    )
    response = sg.send(message)
    print(f"Ã°ÂÂÂ¨ Email sent to {manager_email}, status {response.status_code}")
