"""Checkout settlement receipts and invoice workflow.

Revision ID: 20260602_0005
Revises: 20260602_0004
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0005"
down_revision: Union[str, Sequence[str], None] = "20260602_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkout_receipts (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            booking_id INTEGER NOT NULL,
            folio_id INTEGER NOT NULL,
            receipt_number VARCHAR(80) UNIQUE NOT NULL,
            invoice_number VARCHAR(80) UNIQUE,
            guest_name VARCHAR(150),
            currency VARCHAR(10) DEFAULT 'ETB',
            total_charges NUMERIC(12, 2) DEFAULT 0,
            total_payments NUMERIC(12, 2) DEFAULT 0,
            balance NUMERIC(12, 2) DEFAULT 0,
            payment_method VARCHAR(80),
            payment_amount NUMERIC(12, 2) DEFAULT 0,
            status VARCHAR(50) DEFAULT 'issued',
            receipt_payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkout_receipts_booking ON checkout_receipts(property_code, booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkout_receipts_business_date ON checkout_receipts(property_code, business_date)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_notification_outbox (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER,
            public_request_id INTEGER,
            property_code VARCHAR(50) NOT NULL,
            channel VARCHAR(50) NOT NULL,
            recipient TEXT,
            action VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            business_date DATE,
            status VARCHAR(50) NOT NULL DEFAULT 'queued',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS idx_guest_notification_outbox_booking ON guest_notification_outbox(booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_guest_notification_outbox_status ON guest_notification_outbox(status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_guest_notification_outbox_status")
    op.execute("DROP INDEX IF EXISTS idx_guest_notification_outbox_booking")
    op.execute("DROP INDEX IF EXISTS idx_checkout_receipts_business_date")
    op.execute("DROP INDEX IF EXISTS idx_checkout_receipts_booking")
