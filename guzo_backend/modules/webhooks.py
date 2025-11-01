# webhooks.py
"""
Stripe webhook receiver. Run this (Flask) to receive Stripe events (payment_intent.succeeded)
and mark bookings paid in the GuestAssist sheet.

Run:
    export STRIPE_WEBHOOK_SECRET="whsec_..."
    python -m guzo_backend.modules.webhooks
"""
import os
import json
from flask import Flask, request, jsonify
import stripe

from guzo_backend.modules import google_sheets

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_API_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # set this to your endpoint secret

@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        else:
            # Unsafe fallback: parse without verification (only for local testing)
            event = json.loads(payload)
    except Exception as e:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Webhook verification failed:", e)
        return jsonify({"error": "webhook verification failed"}), 400

    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        # We assume booking metadata includes guest_name to map to sheet row
        guest_name = intent.get("metadata", {}).get("guest_name")
        if guest_name:
            google_sheets.update_booking_status(guest_name, status="Paid")
            print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Marked booking for {guest_name} as Paid")
    # return 200
    return jsonify({"received": True})

if __name__ == "__main__":
    # Run local Flask server
    app.run(host="0.0.0.0", port=5000, debug=True)
