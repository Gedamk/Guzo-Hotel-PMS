"""Payment-provider adapter used by the guest booking bot.

Provider credentials stay in environment configuration. The Telebirr and PayPal
helpers intentionally return pending references until real provider adapters are
configured; they do not claim or record a successful payment.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import stripe


def create_payment_intent(amount: Decimal | int | float, currency: str, description: str):
    value = Decimal(str(amount))
    if value <= 0:
        raise ValueError("Payment amount must be greater than zero.")
    return stripe.PaymentIntent.create(
        amount=int((value * 100).quantize(Decimal("1"))),
        currency=currency.strip().lower(),
        description=description.strip(),
    )


def confirm_payment(payment_intent_id: str):
    identifier = payment_intent_id.strip()
    if not identifier:
        raise ValueError("payment_intent_id is required.")
    return stripe.PaymentIntent.confirm(identifier)


def process_telebirr_payment(amount: Decimal | int | float, phone_number: str) -> dict[str, str | float]:
    value = Decimal(str(amount))
    if value <= 0 or not phone_number.strip():
        raise ValueError("A positive amount and phone number are required.")
    return {"status": "pending", "reference": f"TLB-{uuid4().hex[:16].upper()}", "amount": float(value)}


def process_paypal_payment(amount: Decimal | int | float, currency: str) -> dict[str, str | float]:
    value = Decimal(str(amount))
    if value <= 0 or not currency.strip():
        raise ValueError("A positive amount and currency are required.")
    return {"status": "pending", "transaction_id": f"PPL-{uuid4().hex[:16].upper()}", "amount": float(value), "currency": currency.upper()}
