# -*- coding: utf-8 -*-
"""
Payment Webhooks
Handles asynchronous payment confirmations from Stripe, Telebirr, and PayPal.
"""

import os
import json
from flask import Flask, request, jsonify
import stripe
from guzo_booking_bot.modules import payment_receipts

# Load secrets
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # must set in Stripe dashboard
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Flask app
app = Flask(__name__)


# ==============================
# STRIPE WEBHOOK
# ==============================
@app.route("/webhooks/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid Stripe signature"}), 400

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        booking = {"Guest Name": intent.get("metadata", {}).get("guest", "Unknown")}
        print(f"✅ Stripe payment succeeded: {intent['id']}")

        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Stripe",
            amount=intent["amount_received"] / 100,
            currency=intent["currency"],
            status="Succeeded",
            reference=intent["id"],
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        print(f"❌ Stripe payment failed: {intent['id']}")

    return jsonify({"status": "ok"}), 200


# ==============================
# TELEBIRR WEBHOOK
# ==============================
@app.route("/webhooks/telebirr", methods=["POST"])
def telebirr_webhook():
    try:
        data = request.json
        booking = {"Guest Name": data.get("customerName", "Unknown")}
        status = data.get("status", "failed")
        ref = data.get("transaction_id", "N/A")

        print(f"🔔 Telebirr callback received: {ref}, status={status}")

        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Telebirr",
            amount=float(data.get("amount", 0)),
            currency="ETB",
            status=status,
            reference=ref,
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Telebirr webhook error: {e}")
        return jsonify({"error": str(e)}), 400


# ==============================
# PAYPAL WEBHOOK
# ==============================
@app.route("/webhooks/paypal", methods=["POST"])
def paypal_webhook():
    try:
        data = request.json
        event_type = data.get("event_type", "unknown")

        if event_type == "PAYMENT.SALE.COMPLETED":
            sale = data["resource"]
            booking = {"Guest Name": sale.get("payer", {}).get("payer_info", {}).get("first_name", "Unknown")}
            print(f"✅ PayPal payment completed: {sale['id']}")

            receipt = payment_receipts.generate_receipt(
                booking=booking,
                provider="PayPal",
                amount=float(sale["amount"]["total"]),
                currency=sale["amount"]["currency"],
                status="Completed",
                reference=sale["id"],
            )
            payment_receipts.send_receipt(receipt, manager_alert=True)

        elif event_type == "PAYMENT.SALE.DENIED":
            print("❌ PayPal payment denied.")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ PayPal webhook error: {e}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
