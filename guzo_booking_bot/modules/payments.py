# -*- coding: utf-8 -*-
"""
Payment Service Module
Handles guest payments via Stripe, Telebirr, and PayPal.
Automatically generates and sends multilingual receipts.
"""
# Add a comment at the top
# Payment Service Module - Updated with secure receipts

import os
import stripe
import requests
import paypalrestsdk
from dotenv import load_dotenv
from guzo_booking_bot.modules import payment_receipts

# ==============================
# Load secrets
# ==============================
load_dotenv()

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Telebirr
TELEBIRR_API_KEY = os.getenv("TELEBIRR_API_KEY")
TELEBIRR_API_URL = os.getenv("TELEBIRR_API_URL", "https://api.telebirr.com/payments")

# PayPal
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # "live" in production

if PAYPAL_CLIENT_ID and PAYPAL_SECRET:
    paypalrestsdk.configure({
        "mode": PAYPAL_MODE,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_SECRET,
    })


# ==============================
# STRIPE PAYMENT
# ==============================
def create_payment_intent(booking, amount: int, currency: str = "usd", description: str = "Guzo Guest Assist Payment"):
    """
    Create a Stripe PaymentIntent and trigger receipt on success.
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            description=description,
            automatic_payment_methods={"enabled": True},
        )
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Stripe PaymentIntent created: {intent['id']} for {amount/100:.2f} {currency.upper()}")

        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Stripe",
            amount=amount / 100,
            currency=currency,
            status="Pending",
            reference=intent["id"],
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)
        return {"status": "success", "intent": intent}
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to create Stripe PaymentIntent: {e}")
        return {"status": "failed", "error": str(e)}


def confirm_payment(booking, payment_intent_id: str):
    """
    Confirm a Stripe PaymentIntent and send receipt.
    """
    try:
        intent = stripe.PaymentIntent.confirm(payment_intent_id)
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Payment {intent['id']} confirmed, status: {intent['status']}")

        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Stripe",
            amount=intent["amount"] / 100,
            currency=intent["currency"],
            status=intent["status"],
            reference=intent["id"],
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)
        return {"status": "success", "intent": intent}
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Failed to confirm payment {payment_intent_id}: {e}")
        return {"status": "failed", "error": str(e)}


# ==============================
# TELEBIRR PAYMENT
# ==============================
def process_telebirr_payment(booking, amount: float, phone_number: str):
    """
    Process a Telebirr payment (API-ready).
    """
    if not TELEBIRR_API_KEY:
        return {"status": "failed", "error": "Telebirr API key not configured"}

    try:
        payload = {
            "amount": amount,
            "currency": "ETB",
            "phone": phone_number,
            "reference": f"GuzoAssist-{phone_number}"
        }
        headers = {"Authorization": f"Bearer {TELEBIRR_API_KEY}"}

        response = requests.post(TELEBIRR_API_URL, json=payload, headers=headers, timeout=30)
        data = response.json() if response.status_code == 200 else {}

        status = "success" if response.status_code == 200 else "failed"
        reference = data.get("transaction_id", "N/A")

        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Telebirr",
            amount=amount,
            currency="ETB",
            status=status,
            reference=reference,
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)

        return {"status": status, "reference": reference, "raw": data}
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Telebirr error: {e}")
        return {"status": "failed", "error": str(e)}


# ==============================
# PAYPAL PAYMENT
# ==============================
def process_paypal_payment(booking, amount: float, currency: str = "usd"):
    """
    Process a PayPal payment using PayPal SDK.
    """
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": f"{amount:.2f}", "currency": currency.upper()},
                "description": "Guzo Guest Assist Payment"
            }],
            "redirect_urls": {
                "return_url": "https://guzoassist.com/payment/success",
                "cancel_url": "https://guzoassist.com/payment/cancel"
            }
        })

        if payment.create():
            receipt = payment_receipts.generate_receipt(
                booking=booking,
                provider="PayPal",
                amount=amount,
                currency=currency,
                status="Pending",
                reference=payment.id,
            )
            payment_receipts.send_receipt(receipt, manager_alert=True)

            return {
                "status": "pending",
                "payment_id": payment.id,
                "approval_url": payment.links[1].href,
            }
        else:
            return {"status": "failed", "error": payment.error}
    except Exception as e:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ PayPal error: {e}")
        return {"status": "failed", "error": str(e)}
