"""Payment webhook completion and folio deposit posting.

Revision ID: 20260602_0002
Revises: 20260602_0001
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0002"
down_revision: Union[str, Sequence[str], None] = "20260602_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS folio_transactions (
            id SERIAL PRIMARY KEY,
            folio_id INTEGER NOT NULL,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            txn_type VARCHAR(50) NOT NULL,
            category VARCHAR(80) NOT NULL,
            description TEXT,
            amount NUMERIC(12, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'ETB',
            booking_id INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider VARCHAR(80)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS provider_reference VARCHAR(160)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS folio_transaction_id INTEGER")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failed_at TIMESTAMP")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS failure_reason TEXT")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_requests_token ON payment_requests(token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_requests_public_request ON payment_requests(public_request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folio_transactions_folio ON folio_transactions(folio_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_folio_transactions_booking ON folio_transactions(booking_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_folio_transactions_booking")
    op.execute("DROP INDEX IF EXISTS idx_folio_transactions_folio")
    op.execute("DROP INDEX IF EXISTS idx_payment_requests_public_request")
    op.execute("DROP INDEX IF EXISTS idx_payment_requests_token")
