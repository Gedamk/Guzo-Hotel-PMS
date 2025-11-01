# -*- coding: utf-8 -*-
"""
Booking Payment Handler
Handles booking payments by integrating multiple payment providers
(Stripe, Telebirr, PayPal) with fallback logic.
"""

import sys
from datetime import datetime
from guzo_backend.modules import payments


def safe_print(msg: str):
    """Always print safely using original stdout (avoids closed stream errors)."""
    try:
        sys.__stdout__.write(msg + "\n")
    except Exception:
        pass


def process_booking_payment(guest_name: str, amount: float, currency: str = "usd", phone: str = None):
    """
    Process booking payment with fallback strategy:
    1. Try Stripe
    2. If Stripe fails ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ try Telebirr (ETB only, requires phone number)
    3. If Telebirr fails ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ try PayPal
    """
    safe_print(f"[INFO] Checking for pending payments for {guest_name}...")

    # 1ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Stripe Payment
    try:
        intent = payments.create_payment_intent(int(amount * 100), currency)
        if intent:
            payments.confirm_payment(intent["id"])
            safe_print(f"[OK] Stripe payment successful for {guest_name}")
            return {"status": "success", "provider": "Stripe", "id": intent["id"]}
    except Exception as e:
        safe_print(f"[WARN] Stripe payment failed for {guest_name}: {e}")

    # 2ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ Telebirr Payment (fallback)
    if currency.lower() == "etb" and phone:
        try:
            telebirr_tx = payments.process_telebirr_payment(amount, phone)
            if telebirr_tx.get("status") == "pending":
                safe_print(f"[OK] Telebirr payment initiated for {guest_name}, ref {telebirr_tx['reference']}")
                return {"status": "pending", "provider": "Telebirr", "reference": telebirr_tx["reference"]}
        except Exception as e:
            safe_print(f"[WARN] Telebirr payment failed for {guest_name}: {e}")

    # 3ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ PayPal Payment (last fallback)
    try:
        paypal_tx = payments.process_paypal_payment(amount, currency)
        if paypal_tx.get("status") == "pending":
            safe_print(f"[OK] PayPal payment started for {guest_name}, transaction {paypal_tx['transaction_id']}")
            return {"status": "pending", "provider": "PayPal", "transaction_id": paypal_tx["transaction_id"]}
    except Exception as e:
        safe_print(f"[WARN] PayPal payment failed for {guest_name}: {e}")

    # ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ All failed
    safe_print(f"[FAIL] Payment for {guest_name} failed.")
    return {"status": "failed", "provider": None}


def main():
    """Test runner for booking payment handler."""
    test_guest = "Test Guest"
    test_amount = 100.0  # USD or ETB
    test_currency = "usd"
    test_phone = "+251911111111"  # only needed for Telebirr

    result = process_booking_payment(test_guest, test_amount, test_currency, phone=test_phone)
    safe_print(f"[RESULT] Payment handler result: {result}")


if __name__ == "__main__":
    main()
