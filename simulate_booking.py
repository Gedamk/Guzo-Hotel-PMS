# -*- coding: utf-8 -*-
"""
Simulate Booking Message Ã¢ÂÂ Auto Add to Guest Assist & Notify Manager
Author: Guzo Guest Assist Automation
"""

import os
import datetime as dt
from dotenv import load_dotenv
import gspread
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ========== Load environment and Google credentials ==========
base = os.path.dirname(__file__)
load_dotenv(os.path.join(base, ".env"))
creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Google Sheets IDs
GA_ID = os.getenv("GOOGLE_SHEET_ID_GUEST_ASSIST")
HC_ID = os.getenv("GOOGLE_SHEET_ID_HOTEL_CONTACTS")
NL_ID = os.getenv("GOOGLE_SHEET_ID_NOTIFICATIONS")

# SendGrid config
SG_API = os.getenv("SENDGRID_API_KEY")
FROM = os.getenv("FROM_EMAIL", "reports@guzoassist.com")

# ========== Simulate guest message ==========
guest_message = {
    "guest_name": "John Smith",
    "hotel": "Hotel A",
    "check_in": "2025-10-10",
    "check_out": "2025-10-15",
    "source": "WhatsApp",
    "contact": "+251911000000",
    "status": "Pending"
}

# ========== Step 1. Write to Guest Assist Sheet ==========
try:
    sa = gspread.service_account(creds)
    ws = sa.open_by_key(GA_ID).sheet1

    today = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([
        today,
        guest_message["hotel"],
        guest_message["guest_name"],
        guest_message["check_in"],
        guest_message["check_out"],
        "Deluxe",  # Room type for test
        guest_message["source"],
        guest_message["contact"],
        guest_message["status"],
    ])

    print("Ã¢ÂÂ Booking successfully added to Guest Assist sheet.")

except Exception as e:
    print(f"Ã¢ÂÂ Failed to write to Guest Assist: {e}")

# ========== Step 2. Log in Notification Log Sheet ==========
try:
    ws2 = sa.open_by_key(NL_ID).sheet1
    ws2.append_row([
        dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        guest_message["hotel"],
        "WhatsApp",
        f"New booking received for {guest_message['guest_name']} ({guest_message['check_in']} to {guest_message['check_out']})",
        "Logged"
    ])
    print("Ã°ÂÂÂÃ¯Â¸Â Logged event to Notification Log.")
except Exception as e:
    print(f"Ã¢ÂÂ Ã¯Â¸Â Could not log to Notification Log: {e}")

# ========== Step 3. Email hotel manager (notification) ==========
try:
    sa = gspread.service_account(creds)
    hc_ws = sa.open_by_key(HC_ID).sheet1
    hotel_contacts = hc_ws.get_all_records()
    hotel_row = next((r for r in hotel_contacts if r["Hotel Name"] == guest_message["hotel"]), None)

    if hotel_row and SG_API:
        manager_email = hotel_row.get("ManagerEmail")
        if manager_email:
            sg = SendGridAPIClient(SG_API)
            message = Mail(
                from_email=FROM,
                to_emails=manager_email,
                subject=f"Ã°ÂÂÂ© New Booking Ã¢ÂÂ {guest_message['hotel']}",
                plain_text_content=f"""
New booking received:
Hotel: {guest_message['hotel']}
Guest: {guest_message['guest_name']}
Dates: {guest_message['check_in']} Ã¢ÂÂ {guest_message['check_out']}
Source: {guest_message['source']}
Contact: {guest_message['contact']}
Status: {guest_message['status']}
            """)
            response = sg.send(message)
            print(f"Ã°ÂÂÂ¨ Manager notified via SendGrid (status {response.status_code}).")
        else:
            print("Ã¢ÂÂ Ã¯Â¸Â No manager email found for that hotel.")
    else:
        print("Ã¢ÂÂ Ã¯Â¸Â Could not find hotel or SendGrid not configured.")
except Exception as e:
    print(f"Ã¢ÂÂ Failed to send manager notification: {e}")
