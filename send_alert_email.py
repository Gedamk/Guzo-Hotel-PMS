# -*- coding: utf-8 -*-
"""
send_alert_email.py – Guzo Guest Assist
---------------------------------------
Checks the system_check_run.log for 'ERROR' entries and emails the
summary report via SendGrid if any issues are found.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables
load_dotenv()

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "system_check_run.log")

def read_log():
    """Read the log file safely and extract lines containing 'ERROR'."""
    if not os.path.exists(LOG_FILE):
        print("❌ Log file not found.")
        return [], []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    errors = [line for line in lines if "ERROR" in line]
    return lines, errors

def send_email(subject, body):
    """Send an email alert via SendGrid."""
    sg_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("ALERT_EMAIL", "your_email@example.com")
    from_email = os.getenv("SENDER_EMAIL", to_email)

    if not sg_key:
        print("❌ Missing SENDGRID_API_KEY in .env")
        return

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=f"<pre style='font-family: monospace;'>{body}</pre>"
    )

    try:
        sg = SendGridAPIClient(sg_key)
        sg.send(message)
        print(f"✅ Alert email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send alert email: {e}")

if __name__ == "__main__":
    lines, errors = read_log()
    if errors:
        subject = f"🚨 Guzo System Alert – {datetime.now():%Y-%m-%d %H:%M:%S}"
        body = "".join(errors[-10:])
        send_email(subject, body)
    else:
        print("✅ No errors found in system_check_run.log")
