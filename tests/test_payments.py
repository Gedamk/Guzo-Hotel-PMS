# -*- coding: utf-8 -*-
"""
Unit tests for the payments module.
"""

import sys, os
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_booking_bot.modules import payments


def test_stripe_payment_intent_creation(monkeypatch):
    """Test creating a Stripe PaymentIntent (mocked)."""

    class DummyIntent:
        id = "pi_test_123"
        status = "requires_payment_method"

        def __getitem__(self, item):
            return getattr(self, item)

    def mock_create(**kwargs):
        return DummyIntent()

    monkeypatch.setattr(payments.stripe.PaymentIntent, "create", mock_create)

    intent = payments.create_payment_intent(500, "usd", "Test Payment")
    assert intent is not None
    assert intent["id"] == "pi_test_123"


def test_stripe_payment_confirm(monkeypatch):
    """Test confirming a Stripe PaymentIntent (mocked)."""

    class DummyIntent:
        id = "pi_test_123"
        status = "succeeded"

        def __getitem__(self, item):
            return getattr(self, item)

    def mock_confirm(payment_intent_id):
        return DummyIntent()

    monkeypatch.setattr(payments.stripe.PaymentIntent, "confirm", mock_confirm)

    intent = payments.confirm_payment("pi_test_123")
    assert intent["status"] == "succeeded"


def test_telebirr_payment():
    """Test Telebirr payment simulation."""
    result = payments.process_telebirr_payment(100, "+251911111111")
    assert result["status"] == "pending"
    assert "reference" in result


def test_paypal_payment():
    """Test PayPal payment simulation."""
    result = payments.process_paypal_payment(50, "usd")
    assert result["status"] == "pending"
    assert "transaction_id" in result
