from log_helper import log_event
import os, datetime
from dotenv import load_dotenv
import sendgrid
from sendgrid.helpers.mail import Mail

base = os.path.dirname(__file__)
load_dotenv(os.path.join(base, ".env"))

API = os.getenv("SENDGRID_API_KEY")
TO = os.getenv("TO_EMAIL", "owner@guzoassist.com")
FROM = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[Guzo Reports]")

year, week, _ = datetime.date.today().isocalendar()
zip_name = f"{year}-week{week}.zip"
zip_path = os.path.join(base, "storage", "archives", zip_name)

msg = (
    "Weekly log archive finished.\n"
    f"File: {zip_name}\n"
    f"Exists: {os.path.exists(zip_path)}\n"
    f"Path: {zip_path}"
)

sg = sendgrid.SendGridAPIClient(API)
email = Mail(
    from_email=FROM,
    to_emails=TO,
    subject=f"{PREFIX} Ã¢ÂÂ Log Archive Completed: {zip_name}",
    plain_text_content=msg
)

try:
    resp = sg.send(email)
    print("Email status:", resp.status_code)
except Exception as e:
    print("Email error:", e)
