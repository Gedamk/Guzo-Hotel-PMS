# guzo_booking_bot/config.py 

import os
from dotenv import load_dotenv

# ---- Base paths ----
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Force .env to override any existing env vars (important on Windows)
load_dotenv(dotenv_path=ENV_PATH, override=True, verbose=False)

# ---- Google Sheets / Credentials ----
GOOGLE_CREDS_FILE = os.path.join(BASE_DIR, "guzo_service.json")

SERVICE_ACCOUNT_FILE = os.getenv(
    "SERVICE_ACCOUNT_FILE",
    os.path.join("guzo_booking_bot", "creds", "guzo_service_account.json")
)

GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", GOOGLE_CREDS_FILE)

# Spreadsheet IDs (all from .env)
SPREADSHEET_GUEST_ASSIST_ID      = os.getenv("SPREADSHEET_GUEST_ASSIST_ID", "")
SPREADSHEET_HOTEL_CONTACTS_ID    = os.getenv("SPREADSHEET_HOTEL_CONTACTS_ID", "")
SPREADSHEET_NOTIFICATIONSLOG_ID  = os.getenv("SPREADSHEET_NOTIFICATIONSLOG_ID", "")

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

# ---- Email ----
EMAIL_PROVIDER        = os.getenv("EMAIL_PROVIDER", "sendgrid").strip().lower()  # sendgrid | gmail

SENDGRID_API_KEY      = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_SENDER_EMAIL = os.getenv("SENDGRID_SENDER_EMAIL", "")
SENDGRID_SENDER_NAME  = os.getenv("SENDGRID_SENDER_NAME", "Guzo Guest Assist")

GMAIL_EMAIL           = os.getenv("GMAIL_EMAIL", "")
GMAIL_PASSWORD        = os.getenv("GMAIL_PASSWORD", "")  # must be 16-char Gmail App Password

# Optional Yahoo (leave blank if not using)
YAHOO_EMAIL           = os.getenv("YAHOO_EMAIL", "")
YAHOO_PASSWORD        = os.getenv("YAHOO_PASSWORD", "")

# ---- Telegram ----
TELEGRAM_TOKEN        = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- Twilio ----
TWILIO_ACCOUNT_SID    = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN     = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER   = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_FROM  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ---- Viber (placeholder) ----
VIBER_API_KEY         = os.getenv("VIBER_API_KEY", "")
VIBER_SENDER_NAME     = os.getenv("VIBER_SENDER_NAME", "Guzo Guest Assist")

# ---- Payments ----
STRIPE_API_KEY        = os.getenv("STRIPE_API_KEY", "")
TELEBIRR_API_KEY      = os.getenv("TELEBIRR_API_KEY", "")

# ---- Misc ----
ENV                   = os.getenv("ENV", "development")

# Debug helper to confirm what file was loaded
def _debug_dump():
    print("ENV_PATH:", ENV_PATH)
    print("EMAIL_PROVIDER:", EMAIL_PROVIDER)
    print("GMAIL_EMAIL:", GMAIL_EMAIL)
    print("GMAIL_PASSWORD length:", len(GMAIL_PASSWORD))
    print("SENDGRID key present:", bool(SENDGRID_API_KEY))
    print("GOOGLE_CREDS_FILE:", GOOGLE_CREDS_FILE)
    print("SERVICE_ACCOUNT_FILE:", SERVICE_ACCOUNT_FILE)
    print("SPREADSHEET_GUEST_ASSIST_ID:", SPREADSHEET_GUEST_ASSIST_ID)
    print("SPREADSHEET_HOTEL_CONTACTS_ID:", SPREADSHEET_HOTEL_CONTACTS_ID)
    print("SPREADSHEET_NOTIFICATIONSLOG_ID:", SPREADSHEET_NOTIFICATIONSLOG_ID)
