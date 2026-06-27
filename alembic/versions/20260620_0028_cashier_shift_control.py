"""Harden cashier shift control and link immutable finance transactions.

Revision ID: 20260620_0028
Revises: 20260619_0027
Create Date: 2026-06-20
"""

from alembic import op


revision = "20260620_0028"
down_revision = "20260619_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cashier_sessions (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            cashier_name VARCHAR(180) NOT NULL,
            opening_float NUMERIC(18,2) NOT NULL DEFAULT 0,
            cash NUMERIC(18,2) NOT NULL DEFAULT 0,
            card NUMERIC(18,2) NOT NULL DEFAULT 0,
            bank_transfer NUMERIC(18,2) NOT NULL DEFAULT 0,
            mobile_money NUMERIC(18,2) NOT NULL DEFAULT 0,
            unassigned NUMERIC(18,2) NOT NULL DEFAULT 0,
            actual_cash NUMERIC(18,2) NOT NULL DEFAULT 0,
            actual_card NUMERIC(18,2) NOT NULL DEFAULT 0,
            actual_bank_transfer NUMERIC(18,2) NOT NULL DEFAULT 0,
            actual_mobile_money NUMERIC(18,2) NOT NULL DEFAULT 0,
            actual_unassigned NUMERIC(18,2) NOT NULL DEFAULT 0,
            expected_total NUMERIC(18,2) NOT NULL DEFAULT 0,
            declared_total NUMERIC(18,2) NOT NULL DEFAULT 0,
            variance NUMERIC(18,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'open',
            notes TEXT,
            opened_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMPTZ,
            closed_by VARCHAR(255),
            manager_approved_by VARCHAR(255),
            manager_approval_reason TEXT
        )
        """
    )
    for statement in (
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS assigned_user_email VARCHAR(255)",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS opened_by VARCHAR(255)",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'ETB'",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS declared_at TIMESTAMPTZ",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS approval_requested_at TIMESTAMPTZ",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
        "ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS closure_report JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE finance_transactions ADD COLUMN IF NOT EXISTS cashier_session_id BIGINT REFERENCES cashier_sessions(id)",
    ):
        op.execute(statement)
    op.execute("ALTER TABLE cashier_sessions ALTER COLUMN closed_at DROP NOT NULL")
    op.execute("ALTER TABLE cashier_sessions ALTER COLUMN closed_at DROP DEFAULT")
    op.execute("UPDATE cashier_sessions SET assigned_user_email = LOWER(cashier_name) WHERE assigned_user_email IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cashier_sessions_property_date ON cashier_sessions(property_code, business_date, id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_finance_transactions_cashier_session ON finance_transactions(cashier_session_id, id)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cashier_active_assignment
        ON cashier_sessions(property_code, business_date, assigned_user_email)
        WHERE status <> 'closed'
        """
    )


def downgrade() -> None:
    # Cashier and financial history is intentionally retained.
    pass
