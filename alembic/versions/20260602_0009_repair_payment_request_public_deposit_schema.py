"""Repair payment request schema for public deposits.

Revision ID: 20260602_0009
Revises: 20260602_0008
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0009"
down_revision: Union[str, Sequence[str], None] = "20260602_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_requests (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20),
            public_request_id INTEGER,
            booking_id INTEGER,
            guest_name VARCHAR(150),
            guest_email VARCHAR(150),
            guest_phone VARCHAR(50),
            amount_etb NUMERIC(12, 2) DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'ETB',
            token VARCHAR(160),
            status VARCHAR(50) DEFAULT 'pending',
            expires_at TIMESTAMP,
            created_by VARCHAR(150) DEFAULT 'booking_hub_staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS property_code VARCHAR(20)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS public_request_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS booking_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_name VARCHAR(150)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_email VARCHAR(150)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(50)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS amount_etb NUMERIC(12, 2) DEFAULT 0")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ETB'")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS token VARCHAR(160)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS created_by VARCHAR(150) DEFAULT 'booking_hub_staff'")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider VARCHAR(80)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider_reference VARCHAR(160)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_transaction_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failed_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failure_reason TEXT")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ALTER COLUMN booking_id DROP NOT NULL")
    op.execute("ALTER TABLE payment_requests ALTER COLUMN token DROP NOT NULL")
    op.execute("UPDATE payment_requests SET currency = COALESCE(currency, 'ETB')")
    op.execute("UPDATE payment_requests SET status = COALESCE(status, 'pending')")
    op.execute("UPDATE payment_requests SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_requests_token_unique
        ON payment_requests (token)
        WHERE token IS NOT NULL
        """
    )


def downgrade() -> None:
    pass
