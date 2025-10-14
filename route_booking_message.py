# -*- coding: utf-8 -*-
"""
Route Booking Message
- Reads hotel contact data from Google Sheets
- Translates guest messages (Amharic, Afaan Oromo, etc.) into English
- Finds hotel by name using fuzzy matching
- Logs booking in Guest Assist sheet
- Logs notification in Notification Log sheet
- Sends email to hotel manager via SendGrid
"""

import os
import datetime as dt
import gspread
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from translate_message import translate_to_english
from detect_hotel_name import detect_hotel_name

# -------- Load environment variables --------
load_dotenv(r"C:\Users\Gedan\Desktop\Guzo\.env")

GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
HC_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS")
NL_ID = os.getenv("GOOGLE_SHEET_ID_NOTIFICATIONS")
CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SG_API = os.getenv("SENDGRID_API_KEY")

# -------- Google Sheets setup --------
gc = gspread.service_account(CREDS)
sheet_guest = gc.open_by_key(GA_ID).sheet1
sheet_hotel = gc.open_by_key(HC_ID).sheet1
sheet_notify = gc.open_by_key(NL_ID).sheet1


# -------- Helper Functions --------
def find_hotel_contact(hotel_name: str):
    """Find the hotel info by name"""
    hotels = sheet_hotel.get_all_records()
    for h in hotels:
        if h.get("Hotel Name", "").strip().lower() == hotel_name.strip().lower():
            return h
    return None


def process_booking(hotel_name, guest_name, original_message, source="Telegram"):
    """Main booking logic"""
    now = dt.datetime.now().isoformat(timespec="seconds")
    hotel_info = find_hotel_contact(hotel_name)

    if not hotel_info:
        print(f"Ã¢ÂÂ Hotel not found in contacts: {hotel_name}")
        return

    manager_email = hotel_info.get("ManagerEmail")
    city = hotel_info.get("City", "")
    lang = hotel_info.get("Language", "")

    # Ã°ÂÂÂ¹ Translate message
    translated_message = translate_to_english(original_message)
    print(f"Ã°ÂÂÂ Translated message: {translated_message}")

    # 1Ã¯Â¸ÂÃ¢ÂÂ£ Add to Guest Assist sheet
    sheet_guest.append_row([
        hotel_name,
        guest_name,
        "",  # Check-in placeholder
        "",  # Check-out placeholder
        "",  # Room type placeholder
        source,
        original_message,  # Original text
        "Pending",
        now
    ])

    # 2Ã¯Â¸ÂÃ¢ÂÂ£ Log to Notification Log sheet
    sheet_notify.append_row([
        dt.date.today().isoformat(),
        hotel_name,
        f"New booking via {source}",
        "Logged"
    ])

    # 3Ã¯Â¸ÂÃ¢ÂÂ£ Send Email Notification via SendGrid
    if manager_email and SG_API:
        sg = SendGridAPIClient(SG_API)
        email_body = (
            f"Dear {hotel_info.get('Manager Name','Manager')},\n\n"
            f"A new booking inquiry has been received from {guest_name}.\n\n"
            f"Ã°ÂÂÂ¹ Original Message:\n{original_message}\n\n"
            f"Ã°ÂÂÂ¹ Translated Message:\n{translated_message}\n\n"
            f"Hotel: {hotel_name}\nCity: {city}\nLanguage: {lang}\n\n"
            f"Ã¢ÂÂ Guzo Guest Assist System"
        )

        email = Mail(
            from_email="reports@guzoassist.com",
            to_emails=manager_email,
            subject=f"[Guzo Booking] New {source} request for {hotel_name}",
            plain_text_content=email_body
        )

        resp = sg.send(email)
        print(f"Ã°ÂÂÂ¨ Manager notified via email ({manager_email}), status {resp.status_code}")
    else:
        print("Ã¢ÂÂ Ã¯Â¸Â Missing manager email or SendGrid API key.")

    print(f"Ã¢ÂÂ Booking successfully processed for: {hotel_name}")


# -------- Main Entry Point --------
if __name__ == "__main__":
    # Example guest message (multilingual test)
    message = "Ã¡ÂÂ¥Ã¡ÂÂ£Ã¡ÂÂ­Ã¡ÂÂÃ¡ÂÂ Ã¡ÂÂ­Ã¡ÂÂÃ¡ÂÂ Ã¡ÂÂ Ã¡ÂÂÃ¡ÂÂµ Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂµ Ã¡ÂÂÃ¡ÂÂ½Ã¡ÂÂµ Ã¡ÂÂ¥Ã¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂÃ¡ÂÂ¢ Hotel A"

    # Load hotel names from Google Sheet
    hotels = [h["Hotel Name"] for h in sheet_hotel.get_all_records() if h.get("Hotel Name")]

    # Detect hotel name automatically (with fuzzy logic)
    detected_hotel = detect_hotel_name(message, hotels)

    if detected_hotel:
        process_booking(detected_hotel, "Gedan", message, "Telegram")
    else:
        print("Ã¢ÂÂ Could not detect hotel name in message.")
