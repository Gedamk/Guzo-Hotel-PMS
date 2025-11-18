# -*- coding: utf-8 -*-
"""
email_listener.py – check inbox for new booking emails
"""

import imaplib, email, time, os
from dotenv import load_dotenv
from auto_email_reply import send_auto_reply
from guzo_booking_bot.modules import google_sheets

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_ADDRESS")   # info@guzoassist.com
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")  # app password (not your main password)
IMAP_SERVER = "imap.privateemail.com"     # if using Namecheap Private Email

def check_inbox():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    _, data = mail.search(None, '(UNSEEN SUBJECT "Booking")')
    mail_ids = data[0].split()

    for num in mail_ids:
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = msg["subject"]
        sender = msg["from"]

        # Parse email body
        if msg.is_multipart():
            body = msg.get_payload(0).get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()

        print(f"📨 New booking email from {sender}: {subject}")

        # Example parse: extract hotel name, date, and guest name from message text
        guest_name = "Unknown"
        if "Name:" in body:
            guest_name = body.split("Name:")[1].split("\n")[0].strip()

        # Log to Google Sheets
        google_sheets.add_booking({
            "Guest": guest_name,
            "Source": "Email",
            "Status": "Pending",
            "Email": sender
        })

        # Send confirmation back to guest
        send_auto_reply(sender, guest_name)

        # Mark as seen
        mail.store(num, '+FLAGS', '\\Seen')

    mail.logout()

if __name__ == "__main__":
    while True:
        check_inbox()
        time.sleep(60)  # check every 1 minute
