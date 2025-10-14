# -*- coding: utf-8 -*-
"""
send_log_email.py
Only send the latest bot log if errors or warnings are detected.
"""

import os
import glob
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("GUZO_EMAIL", "guzoassist@gmail.com")
SENDER_PASS = os.getenv("GUZO_EMAIL_PASS")
RECIPIENT = "manager@guzoassist.com"

LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    print("No logs directory found.")
    exit()

# Find the newest log file
log_files = glob.glob(os.path.join(LOG_DIR, "bot_*.log"))
if not log_files:
    print("No log files found.")
    exit()

latest_log = max(log_files, key=os.path.getctime)

# Check log content for problems
with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read().lower()

problem_keywords = ["error", "exception", "traceback", "failed", "unauthorized", "denied"]
if not any(k in content for k in problem_keywords):
    print("✅ No errors found — skipping email.")
    exit()

# Create email alert
msg = EmailMessage()
msg["Subject"] = f"⚠️ GuzoBot Alert – Issue Detected in {os.path.basename(latest_log)}"
msg["From"] = SENDER_EMAIL
msg["To"] = RECIPIENT
msg.set_content("The latest GuzoBot log contains warnings or errors. See attached for details.")

with open(latest_log, "rb") as f:
    msg.add_attachment(f.read(), maintype="text", subtype="plain", filename=os.path.basename(latest_log))

# Send email via Gmail
try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASS)
        smtp.send_message(msg)
        print(f"⚠️ Alert email sent to {RECIPIENT}")
except Exception as e:
    print(f"❌ Failed to send alert email: {e}")
