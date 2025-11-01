from guzo_backend.modules.booking import get_notification_sheet
from datetime import datetime

# --- Example stubs for sending ---
def send_email(to_email, subject, body, booking_id=None, guest=None):
    # Actual email sending happens here...
    status = "SUCCESS"
    log_notification(booking_id, guest, "Email", to_email, body, status)

def send_sms(to_phone, message, booking_id=None, guest=None):
    # Actual SMS sending via Twilio...
    status = "SUCCESS"
    log_notification(booking_id, guest, "SMS", to_phone, message, status)

def send_whatsapp(to_phone, message, booking_id=None, guest=None):
    # Actual WhatsApp sending via Twilio...
    status = "SUCCESS"
    log_notification(booking_id, guest, "WhatsApp", to_phone, message, status)

def send_telegram(chat_id, message, booking_id=None, guest=None):
    # Actual Telegram sending...
    status = "SUCCESS"
    log_notification(booking_id, guest, "Telegram", chat_id, message, status)

def send_viber(to_phone, message, booking_id=None, guest=None):
    # Placeholder for Viber integration
    status = "FAILED"
    log_notification(booking_id, guest, "Viber", to_phone, message, status)

# --- Log every notification in NotificationLogs ---
def log_notification(booking_id, guest, channel, contact, message, status):
    ws = get_notification_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([booking_id, guest, channel, contact, message, status, timestamp])
    print(f"ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Notification logged: {booking_id} | {channel} | {status}")
