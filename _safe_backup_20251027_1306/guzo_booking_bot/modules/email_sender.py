# -*- coding: utf-8 -*-
"""
email_sender.py – Secure multilingual email delivery for Guzo Guest Assist.
---------------------------------------------------------------------------
Handles all transactional, booking, and report emails via SendGrid.
Uses domain-authenticated sender (reports@guzoassist.com) for best deliverability.
"""

import os
import base64
import logging
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

# -------------------------------------------------------------
# Environment setup
# -------------------------------------------------------------
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "reports@guzoassist.com")

logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# Core email sender
# -------------------------------------------------------------
def send_invoice_email(to_email: str, subject: str, body_text: str, pdf_path: str = None):
    """
    Send an email with optional PDF attachment (invoice, report, etc.).
    """
    if not SENDGRID_API_KEY:
        logger.error("❌ Missing SENDGRID_API_KEY in environment.")
        print("❌ Missing SENDGRID_API_KEY in environment.")
        return False

    if not to_email:
        logger.error("❌ Missing recipient email address.")
        return False

    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=body_text,
        )

        # ---------------------------------------------------------
        # Optional PDF attachment
        # ---------------------------------------------------------
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as f:
                    encoded_file = base64.b64encode(f.read()).decode()
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(os.path.basename(pdf_path)),
                    FileType("application/pdf"),
                    Disposition("attachment"),
                )
                message.attachment = attachment
                logger.info(f"📎 Attached file: {os.path.basename(pdf_path)}")
            except Exception as e:
                logger.warning(f"⚠️ Could not attach file: {e}")

        # ---------------------------------------------------------
        # Send email
        # ---------------------------------------------------------
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 202):
            print(f"✅ Email successfully sent to {to_email}")
            logger.info(f"✅ Email successfully sent to {to_email}")
            return True
        else:
            print(f"⚠️ Email failed with status {response.status_code}")
            logger.error(f"⚠️ Email failed with status {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"⚠️ Email sending failed: {e}")
        print(f"⚠️ Email sending failed: {e}")
        return False


# -------------------------------------------------------------
# Direct test mode
# -------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Testing Guzo Guest Assist email sender...")
    success = send_invoice_email(
        to_email=os.getenv("TO_EMAIL", "owner@guzoassist.com"),
        subject="✅ Guzo Guest Assist Automated Email Test",
        body_text="<strong>Your SendGrid configuration is working perfectly!</strong>",
    )
    if success:
        print("✅ Test completed successfully.")
    else:
        print("⚠️ Test failed. Please check your SendGrid credentials or domain setup.")
