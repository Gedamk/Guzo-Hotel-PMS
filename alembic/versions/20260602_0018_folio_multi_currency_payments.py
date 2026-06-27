"""Add folio payment multi-currency accounting fields.

Revision ID: 20260602_0018
Revises: 20260602_0017
Create Date: 2026-06-06
"""

from alembic import op


revision = "20260602_0018"
down_revision = "20260602_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS original_amount NUMERIC(12, 2)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS original_currency VARCHAR(10)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_to_base NUMERIC(18, 8)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS base_amount NUMERIC(14, 2)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS base_currency VARCHAR(10) DEFAULT 'ETB'")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_source VARCHAR(80)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_overridden BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS exchange_rate_override_reason TEXT")
    op.execute(
        """
        UPDATE folio_transactions
        SET original_amount = COALESCE(original_amount, amount),
            original_currency = COALESCE(NULLIF(TRIM(original_currency), ''), currency),
            exchange_rate_to_base = CASE
                WHEN COALESCE(NULLIF(TRIM(currency), ''), 'ETB') = 'ETB'
                    THEN COALESCE(exchange_rate_to_base, 1)
                ELSE exchange_rate_to_base
            END,
            base_currency = COALESCE(NULLIF(TRIM(base_currency), ''), 'ETB'),
            base_amount = CASE
                WHEN COALESCE(NULLIF(TRIM(currency), ''), 'ETB') = 'ETB'
                    THEN COALESCE(base_amount, amount)
                ELSE base_amount
            END,
            exchange_rate_source = CASE
                WHEN COALESCE(NULLIF(TRIM(currency), ''), 'ETB') = 'ETB'
                    THEN COALESCE(exchange_rate_source, 'same_currency')
                ELSE COALESCE(exchange_rate_source, 'legacy_unconverted')
            END,
            exchange_rate_overridden = COALESCE(exchange_rate_overridden, FALSE)
        WHERE txn_type = 'payment'
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_folio_transactions_base_currency ON folio_transactions(base_currency)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_folio_transactions_original_currency ON folio_transactions(original_currency)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_folio_transactions_original_currency")
    op.execute("DROP INDEX IF EXISTS ix_folio_transactions_base_currency")
