# -*- coding: utf-8 -*-
"""
payment_handler.py â Guzo Guest Assist Secure Payment Module
-------------------------------------------------------------
Handles payment detection, Chapa payment link generation,
Google Sheet updates, and branded PDF invoice emails.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from guzo_backend.modules.google_sheets import update_payment_status
from guzo_backend.modules.invoice_generator import generate_invoice_pdf
from guzo_backend.modules.notifications import send_email

# -------------------------------------------------------------
# Setup
# -------------------------------------------------------------
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

CHAPA_PUBLIC_KEY = os.getenv("CHAPA_PUBLIC_KEY")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "reservations@guzoassist.com")

# -------------------------------------------------------------
# Payment Link Generator (mock / placeholder)
# -------------------------------------------------------------
def generate_payment_link(reference: str, amount: str, currency="ETB") -> str:
    """
    Generate secure Chapa payment link (mocked).
    Replace this with real Chapa API request in production.
    """
    chapa_url = f"https://chapa.co/pay/{reference}"
    logger.info(f"Generated payment link: {chapa_url} ({amount} {currency})")
    return chapa_url

# -------------------------------------------------------------
# Payment Processor
# -------------------------------------------------------------
def process_payment(reference_id: str, guest_name: str, guest_email: str, amount: str, currency="ETB"):
    """
    1. Generate payment link
    2. Simulate webhook callback success
    3. Update Google Sheet
    4. Send invoice PDF via email
    """
    logger.info(f"í´ Processing payment for {guest_name} ({reference_id})")

    # 1ï¸â£ Generate payment link
    payment_link = generate_payment_link(reference_id, amount, currency)

    # 2ï¸â£ Simulate successful webhook
    paid = update_payment_status(reference_id, amount, currency)
    if not paid:
        logger.warning("â ï¸ Google Sheet update failed.")
        return False

    # 3ï¸â£ Generate invoice PDF
    invoice_path = generate_invoice_pdf(
        guest_name=guest_name,
        amount=amount,
        currency=currency,
        confirmation_id=reference_id,
        hotel_name="Guzo Partner Hotel",
    )

    # 4ï¸â£ Send invoice email
    subject = f"Payment Confirmation â {reference_id}"
    body = (
        f"Dear {guest_name},\n\n"
        f"Weâve received your payment of {amount} {currency}.\n"
        f"Your reference ID is {reference_id}.\n\n"
        f"Attached is your invoice.\n\n"
        f"Warm regards,\nGuzo Guest Assist Team"
    )

    send_email(to_email=guest_email, subject=subject, body=body, attachment_path=invoice_path)
    logger.info(f"â Payment processed & invoice sent to {guest_email}")
    return True
