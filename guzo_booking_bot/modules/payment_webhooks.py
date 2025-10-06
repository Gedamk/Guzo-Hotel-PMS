# -*- coding: utf-8 -*-
"""
Payment Webhooks
Handles asynchronous payment events from Stripe, Telebirr, and PayPal.
"""

import os
from flask import Flask, request, jsonify
from guzo_booking_bot.modules import payment_receipts

app = Flask(__name__)

# =========================
# Stripe Webhook
# =========================
@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data.decode("utf-8")
    event = request.json

    # Log received event
    print(f"[Stripe Webhook] Event received: {event.get('type')}")

    if event.get("type") == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        booking = {"Guest Name": payment_intent.get("metadata", {}).get("guest_name", "Unknown")}
        receipt = payment_receipts.generate_receipt(
            booking=booking,
            provider="Stripe",
            amount=payment_intent["amount"] / 100,
            currency=payment_intent["currency"],
            status="Succeeded",
            reference=payment_intent["id"],
        )
        payment_receipts.send_receipt(receipt, manager_alert=True)

    return jsonify({"status": "ok"}), 200


# =========================
# Telebirr Webhook (placeholder)
# =========================
@app.route("/webhook/telebirr", methods=["POST"])
def telebirr_webhook():
    data = request.json
    print(f"[Telebirr Webhook] Event received: {data}")

    booking = {"Guest Name": data.get("guest_name", "Unknown")}
    receipt = payment_receipts.generate_receipt(
        booking=booking,
        provider="Telebirr",
        amount=data.get("amount", 0),
        currency="ETB",
        status=data.get("status", "pending"),
        reference=data.get("reference", "TB-REF"),
    )
    payment_receipts.send_receipt(receipt, manager_alert=True)

    return jsonify({"status": "ok"}), 200


# =========================
# PayPal Webhook (placeholder)
# =========================
@app.route("/webhook/paypal", methods=["POST"])
def paypal_webhook():
    data = request.json
    print(f"[PayPal Webhook] Event received: {data}")

    booking = {"Guest Name": data.get("guest_name", "Unknown")}
    receipt = payment_receipts.generate_receipt(
        booking=booking,
        provider="PayPal",
        amount=data.get("amount", 0),
        currency=data.get("currency", "USD"),
        status=data.get("status", "pending"),
        reference=data.get("transaction_id", "PP-REF"),
    )
    payment_receipts.send_receipt(receipt, manager_alert=True)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 5001))
    print(f"[INFO] Starting Payment Webhooks on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
