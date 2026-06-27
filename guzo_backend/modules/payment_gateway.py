# -*- coding: utf-8 -*-
"""
payment_gateway.py
----------------------------------------------------
Handles Chapa payment link generation and webhook verification
for Guzo Guest Assist (supports local + international guests).
"""

import os
import requests
import uuid
import hmac
import hashlib

# ──────────────────────────────────────────────────────────────
# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

CHAPA_URL = os.getenv("CHAPA_PAYMENT_BASE_URL", "https://api.chapa.co/v1/transaction/initialize")
CHAPA_KEY = os.getenv("CHAPA_SECRET_KEY")
RETURN_URL = os.getenv("CHAPA_RETURN_URL", "https://your-domain.com/payment_return")
WEBHOOK_URL = os.getenv("CHAPA_WEBHOOK_URL", "https://your-domain.com/chapa_webhook")
WEBHOOK_SECRET = os.getenv("CHAPA_WEBHOOK_SECRET", "")

# ──────────────────────────────────────────────────────────────
def generate_chapa_link(booking_id: str, amount: float, currency: str = "ETB", guest_email: str = "") -> str:
    """
    Generates a secure Chapa checkout link for payment.
    """
    try:
        reference = f"{booking_id}-{uuid.uuid4().hex[:8]}"
        payload = {
            "amount": amount,
            "currency": currency,
            "email": guest_email,
            "callback_url": RETURN_URL,
            "reference": reference,
            "webhook_url": WEBHOOK_URL,
        }

        headers = {
            "Authorization": f"Bearer {CHAPA_KEY}",
            "Content-Type": "application/json",
        }

        response = requests.post(CHAPA_URL, json=payload, headers=headers)
        data = response.json()

        if data.get("status") == "success":
            print(f"✅ Chapa payment link generated for {guest_email}: {data['data']['checkout_url']}")
            return data["data"]["checkout_url"]
        else:
            print("⚠️ Failed to generate Chapa payment link:", data)
            return None
    except Exception as e:
        print("❌ Error generating payment link:", e)
        return None


# ──────────────────────────────────────────────────────────────
def verify_webhook_signature(payload: bytes, signature_header: str) -> bool:
    """
    Verifies Chapa webhook authenticity.
    """
    try:
        computed = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature_header)
    except Exception as e:
        print("⚠️ Webhook signature verification failed:", e)
        return False
