# -*- coding: utf-8 -*-
"""
email_receiver.py
Reads unread booking emails from Gmail and logs them.
"""

import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
from guzo_booking_bot.utils.sheet_logger import log_message
from guzo_booking_bot.utils.email_sender import send_notification

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

print(f"[DEBUG] Loaded EMAIL_ADDRESS: {EMAIL_ADDRESS}")

def clean_subject(subject):
    """Decode email subject safely."""
    if subject is None:
        return "(No Subject)"
    if isinstance(subject, bytes):
        try:
            return subject.decode()
        except Exception:
            return subject.decode("utf-8", errors="ignore")
    return subject

def fetch_unread_emails():
    """Fetch unread booking emails from Gmail."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[WARN] Missing EMAIL_ADDRESS or EMAIL_PASSWORD in .env")
        return

    try:
        # Connect securely to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        status, messages = mail.search(None, "(UNSEEN)")
        email_ids = messages[0].split()

        if not email_ids:
            print("[INFO] No new unread emails.")
            mail.logout()
            return

        for eid in email_ids:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject, encoding = decode_header(msg["Subject"])[0]
                    subject = clean_subject(subject)
                    from_ = msg.get("From")

                    # Extract plain text content
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    print(f"[EMAIL] New booking email from {from_}: {subject}")
                    log_message("email", from_, body)

                    # Optional confirmation back to sender
                    send_notification("Booking Received", f"Your booking request was received.\n\n{body}")

        mail.logout()

    except Exception as e:
        print(f"[ERROR] Failed to fetch emails: {e}")

if __name__ == "__main__":
    print(f"[DEBUG] Checking Gmail for unread messages using: {EMAIL_ADDRESS}")
    fetch_unread_emails()
