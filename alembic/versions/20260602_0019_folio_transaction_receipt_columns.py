"""Add optional folio transaction receipt columns.

Revision ID: 20260602_0019
Revises: 20260602_0018
Create Date: 2026-06-06
"""

from alembic import op


revision = "20260602_0019"
down_revision = "20260602_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS payment_method VARCHAR(80)")
    op.execute("ALTER TABLE folio_transactions ADD COLUMN IF NOT EXISTS reference VARCHAR(160)")


def downgrade() -> None:
    pass
