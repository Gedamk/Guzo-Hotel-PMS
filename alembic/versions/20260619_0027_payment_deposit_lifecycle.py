"""Add production payment and deposit lifecycle tables.

Revision ID: 20260619_0027
Revises: 20260619_0026
Create Date: 2026-06-19
"""

from alembic import op


revision = "20260619_0027"
down_revision = "20260619_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS deposit_accounts (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            booking_id BIGINT,
            public_request_id BIGINT,
            payment_request_id BIGINT,
            folio_id BIGINT,
            business_date DATE NOT NULL,
            required_amount NUMERIC(18,2) NOT NULL CHECK (required_amount >= 0),
            requested_amount NUMERIC(18,2) NOT NULL CHECK (requested_amount >= 0),
            paid_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
            allocated_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (allocated_amount >= 0),
            transferred_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (transferred_amount >= 0),
            refunded_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (refunded_amount >= 0),
            forfeited_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (forfeited_amount >= 0),
            currency VARCHAR(10) NOT NULL DEFAULT 'ETB',
            refundable BOOLEAN NOT NULL DEFAULT TRUE,
            status VARCHAR(30) NOT NULL DEFAULT 'requested'
                CHECK (status IN ('requested','partial','paid','allocated','transferred','partially_refunded','refunded','forfeited','cancelled')),
            payment_method VARCHAR(80),
            reference VARCHAR(255),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (booking_id IS NOT NULL OR public_request_id IS NOT NULL),
            UNIQUE (property_code, booking_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS deposit_events (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            deposit_account_id BIGINT NOT NULL REFERENCES deposit_accounts(id),
            event_type VARCHAR(30) NOT NULL
                CHECK (event_type IN ('requested','receipt','allocated','transferred','refunded','forfeited','cancelled')),
            amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
            currency VARCHAR(10) NOT NULL,
            payment_method VARCHAR(80),
            reference VARCHAR(255),
            finance_transaction_id BIGINT REFERENCES finance_transactions(id),
            idempotency_key VARCHAR(180) NOT NULL,
            audit_reference VARCHAR(120) NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE (property_code, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_batches (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            booking_id BIGINT,
            folio_id BIGINT,
            account_reference VARCHAR(180),
            requested_amount NUMERIC(18,2) NOT NULL CHECK (requested_amount > 0),
            received_amount NUMERIC(18,2) NOT NULL CHECK (received_amount > 0),
            overpayment_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (overpayment_amount >= 0),
            currency VARCHAR(10) NOT NULL,
            status VARCHAR(30) NOT NULL CHECK (status IN ('partial','paid','overpaid','voided','corrected')),
            reference VARCHAR(255),
            idempotency_key VARCHAR(180) NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (property_code, idempotency_key),
            CHECK (folio_id IS NOT NULL OR booking_id IS NOT NULL OR account_reference IS NOT NULL)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            payment_batch_id BIGINT NOT NULL REFERENCES payment_batches(id),
            payment_method VARCHAR(80) NOT NULL,
            amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
            reference VARCHAR(255),
            finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),
            folio_transaction_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_deposit_accounts_property_status ON deposit_accounts(property_code, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payment_batches_property_date ON payment_batches(property_code, business_date)")
    op.execute("ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS deposit_account_id BIGINT")


def downgrade() -> None:
    # Payment and deposit history is financial evidence and must not be dropped.
    pass
