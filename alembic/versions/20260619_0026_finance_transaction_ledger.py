"""Add immutable finance transaction ledger.

Revision ID: 20260619_0026
Revises: 20260618_0025
Create Date: 2026-06-19
"""

from alembic import op


revision = "20260619_0026"
down_revision = "20260618_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_transactions (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            folio_id BIGINT,
            booking_id BIGINT,
            account_reference VARCHAR(180),
            transaction_type VARCHAR(30) NOT NULL
                CHECK (transaction_type IN (
                    'charge', 'payment', 'deposit', 'refund', 'void',
                    'correction', 'transfer', 'adjustment'
                )),
            amount NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
            currency VARCHAR(10) NOT NULL,
            direction VARCHAR(10) NOT NULL CHECK (direction IN ('debit', 'credit')),
            payment_method VARCHAR(80),
            reference VARCHAR(255),
            source_document_type VARCHAR(80),
            source_document_id VARCHAR(120),
            reversal_of_transaction_id BIGINT REFERENCES finance_transactions(id),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            idempotency_key VARCHAR(180) NOT NULL,
            audit_reference VARCHAR(120) NOT NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT finance_transaction_account_reference_check CHECK (
                folio_id IS NOT NULL OR booking_id IS NOT NULL OR account_reference IS NOT NULL
            ),
            CONSTRAINT uq_finance_transaction_idempotency UNIQUE (property_code, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_finance_transaction_reversal
        ON finance_transactions(reversal_of_transaction_id)
        WHERE reversal_of_transaction_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_finance_transactions_property_date
        ON finance_transactions(property_code, business_date, id)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_finance_transaction_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'finance_transactions is immutable; post a reversal instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS finance_transactions_immutable_update ON finance_transactions")
    op.execute("DROP TRIGGER IF EXISTS finance_transactions_immutable_delete ON finance_transactions")
    op.execute(
        """
        CREATE TRIGGER finance_transactions_immutable_update
        BEFORE UPDATE ON finance_transactions
        FOR EACH ROW EXECUTE FUNCTION prevent_finance_transaction_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER finance_transactions_immutable_delete
        BEFORE DELETE ON finance_transactions
        FOR EACH ROW EXECUTE FUNCTION prevent_finance_transaction_mutation()
        """
    )


def downgrade() -> None:
    # Financial ledgers are intentionally retained. Destructive downgrade is prohibited.
    pass
