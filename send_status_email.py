from log_helper import log_event
import os
import datetime
import sendgrid
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# ==========================================================
# GUZO - STATUS EMAIL SCRIPT (with logging)
# ==========================================================

# -------------------------------
# Load environment variables
# -------------------------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
print("DEBUG: Loading .env from:", dotenv_path)
load_dotenv(dotenv_path=dotenv_path)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TO_EMAIL = os.getenv("TO_EMAIL", "owner@guzoassist.com")
FROM_EMAIL = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[Guzo Reports]")

status_file = os.path.join(os.path.dirname(__file__), "logs", "latest_status.txt")
log_file = os.path.join(os.path.dirname(__file__), "logs", "all_jobs.log")

# -------------------------------
# Helper: Write to all_jobs.log
# -------------------------------
def log_message(message: str):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"{timestamp} {message}\n")
    print(message)

# -------------------------------
# Main function
# -------------------------------
def send_status():
    if not SENDGRID_API_KEY:
        log_message("Ã¢ÂÂ ERROR: SENDGRID_API_KEY not found in environment variables")
        raise ValueError("SENDGRID_API_KEY not found in environment variables")

    # Read latest status text
    if os.path.exists(status_file):
        with open(status_file, "r", encoding="utf-8") as f:
            status_text = f.read()
    else:
        status_text = "Ã¢ÂÂ Ã¯Â¸Â No status file found. Check logs folder."

    # Decide subject
    if "error" in status_text.lower() or "fail" in status_text.lower():
        subject = f"{SUBJECT_PREFIX} Ã¢ÂÂ Ã¯Â¸Â ERROR Ã¢ÂÂ Check Logs"
    else:
        subject = f"{SUBJECT_PREFIX} Ã¢ÂÂ OK Ã¢ÂÂ Guzo Daily Report"

    # Create SendGrid message
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=subject,
        plain_text_content=status_text
    )

    # Attempt to send
    try:
        response = sg.send(message)
        if response.status_code == 202:
            log_message(f"Ã¢ÂÂ Email sent successfully: {subject}")
        else:
            log_message(f"Ã¢ÂÂ Ã¯Â¸Â Email sent with unexpected status: {response.status_code}")
    except Exception as e:
        log_message(f"Ã¢ÂÂ Error sending email: {e}")

# -------------------------------
# Run the script
# -------------------------------
if __name__ == "__main__":
    print("DEBUG: SENDGRID_API_KEY configured:", bool(SENDGRID_API_KEY))
    send_status()
