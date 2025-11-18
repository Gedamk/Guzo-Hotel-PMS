# -*- coding: utf-8 -*-
"""
email_sender.py – Guzo Guest Assist Email Utility (v4.0 Global)
---------------------------------------------------------------
Handles transactional and automated booking emails via SendGrid.
Compliant with international hospitality communication standards.
"""

import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from pathlib import Path

print("🚀 Starting email_sender.py (production mode)")

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================
BASE_DIR = Path(__file__).resolve().parents[2]
dotenv_path = BASE_DIR / ".env"
print("🔍 Loading .env from:", dotenv_path)

if load_dotenv(dotenv_path):
    print("✅ .env file loaded successfully")
else:
    print("⚠️ Could not load .env file — please check path")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
DEFAULT_SENDER = os.getenv("DEFAULT_SENDER_EMAIL", "no-reply@guzoassist.com")
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "support@guzoassist.com")
TEST_EMAIL = os.getenv("TEST_EMAIL", "nahom2natanim@gmail.com")

print(f"🔑 SENDGRID_API_KEY found: {bool(SENDGRID_API_KEY)}")
print(f"📧 DEFAULT_SENDER_EMAIL: {DEFAULT_SENDER}")
print(f"📩 TEST_EMAIL: {TEST_EMAIL}")

# ============================================================
# GENERIC SEND FUNCTION
# ============================================================
def send_email(to_email, subject, body):
    """Send simple plain-text email using SendGrid (debug/test mode)."""
    print(f"📤 Preparing to send to: {to_email}")
    if not SENDGRID_API_KEY:
        print("❌ SENDGRID_API_KEY missing in .env file.")
        return False

    try:
        message = Mail(
            from_email=DEFAULT_SENDER,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )
        message.reply_to = REPLY_TO_EMAIL
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ Email sent successfully → {to_email}")
        print(f"📨 SendGrid status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"⚠️ Email send failed: {e}")
        return False


# ============================================================
# BOOKING CONFIRMATION EMAIL (AUTO FROM TELEGRAM)
# ============================================================
def send_confirmation_email(to_emails, subject, content, from_email=None):
    """
    Sends multilingual booking confirmation to guest + hotel.
    Automatically triggered by message_router after booking confirmation.
    """
    if not SENDGRID_API_KEY:
        print("❌ SENDGRID_API_KEY missing. Cannot send confirmation email.")
        return False

    if isinstance(to_emails, str):
        to_emails = [to_emails]

    from_email = from_email or DEFAULT_SENDER
    guest = content.get("Guest Name", "Guest")
    hotel = content.get("Hotel Name", "Hotel")
    checkin = content.get("Check-In Date", "—")
    checkout = content.get("Check-Out Date", "—")
    nights = content.get("Nights", "—")
    room = content.get("Room Type", "—")
    total = content.get("Total Revenue (ETB)", "—")
    conf_id = content.get("Confirmation ID", "—")
    phone = content.get("Phone (Front Desk)", "—")
    pay_method = content.get("Payment Method", "—")
    lang = content.get("lang", "en")

    # === Multilingual Greeting ===
    greeting = {
        "en": f"Dear {guest},",
        "am": f"ውድ {guest}፣",
        "om": f"Kabajamoo {guest},"
    }.get(lang, f"Dear {guest},")

    intro = {
        "en": f"We’re delighted to confirm your reservation at <strong>{hotel}</strong>.",
        "am": f"በ<strong>{hotel}</strong> የእርስዎን መያዣ እንደተረጋገጠ ደስ ይላል።",
        "om": f"Turtin kee <strong>{hotel}</strong> irratti mirkanaaʼeera."
    }.get(lang)

    # === HTML Body ===
    html_body = f"""
    <html>
      <body style="font-family:Arial, sans-serif; background:#f5f7fa; padding:25px;">
        <table width="600" align="center" cellpadding="0" cellspacing="0"
               style="background:white; border-radius:10px; overflow:hidden;">
          <tr style="background:#004080; color:white;">
            <td style="padding:20px; font-size:18px; font-weight:bold;">
              🏨 Booking Confirmation – {hotel}
            </td>
          </tr>
          <tr><td style="padding:25px; font-size:15px; color:#333;">
            <p>{greeting}</p>
            <p>{intro}</p>
            <hr style="border:none; border-top:1px solid #ddd;">
            <h3>Reservation Details</h3>
            <table width="100%" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
              <tr><td><strong>Hotel</strong></td><td>{hotel}</td></tr>
              <tr><td><strong>Check-In</strong></td><td>{checkin}</td></tr>
              <tr><td><strong>Check-Out</strong></td><td>{checkout}</td></tr>
              <tr><td><strong>Nights</strong></td><td>{nights}</td></tr>
              <tr><td><strong>Room Type</strong></td><td>{room}</td></tr>
              <tr><td><strong>Payment</strong></td><td>{pay_method}</td></tr>
              <tr><td><strong>Total</strong></td><td>{total} ETB</td></tr>
              <tr><td><strong>Confirmation ID</strong></td><td>{conf_id}</td></tr>
            </table>
            <hr style="border:none; border-top:1px solid #ddd;">
            <p>📞 Front Desk: {phone}<br>
               🌐 <a href="https://guzoassist.com" style="color:#004080;">www.guzoassist.com</a></p>
            <p>✨ Thank you for choosing Guzo Guest Assist. We look forward to welcoming you soon!</p>
            <p style="color:#888; font-size:12px;">This is an automated message, please do not reply.</p>
          </td></tr>
        </table>
      </body>
    </html>
    """

    # === Plain-Text Fallback (for Outlook/basic clients) ===
    plain_body = (
        f"{greeting}\n\n"
        f"We’re delighted to confirm your reservation at {hotel}.\n\n"
        f"📅 Check-In: {checkin}\n"
        f"📅 Check-Out: {checkout}\n"
        f"🛏️ Room Type: {room}\n"
        f"💳 Payment: {pay_method}\n"
        f"💰 Total: {total} ETB\n"
        f"🔖 Confirmation ID: {conf_id}\n\n"
        f"For any assistance, contact {phone}\n"
        f"🌐 www.guzoassist.com\n\n"
        f"✨ Thank you for choosing Guzo Guest Assist."
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        for email in to_emails:
            message = Mail(
                from_email=from_email,
                to_emails=email,
                subject=subject,
                html_content=html_body,
                plain_text_content=plain_body
            )
            message.reply_to = REPLY_TO_EMAIL
            response = sg.send(message)
            print(f"✅ Confirmation email sent to {email} | Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"⚠️ Confirmation email failed: {e}")
        return False


# ============================================================
# TEST MODE (Run Directly)
# ============================================================
if __name__ == "__main__":
    print("🚀 Running Guzo Guest Assist Email Test...")

    subject = "Guzo Guest Assist – Email Test Confirmation"
    body = (
        "Hello Gedan,\n\n"
        "✅ This is a test email from your Guzo Guest Assist system.\n"
        "If you received this, SendGrid setup works correctly.\n\n"
        "Kind regards,\n"
        "Guzo Guest Assist Bot"
    )

    ok = send_email(TEST_EMAIL, subject, body)
    if ok:
        print("✅ [DONE] Test email sent successfully.")
    else:
        print("❌ [ERROR] Could not send test email.")
