"""Night Audit room posting, no-show, and business date lock controls.

Revision ID: 20260602_0003
Revises: 20260602_0002
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0003"
down_revision: Union[str, Sequence[str], None] = "20260602_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS night_audit_postings (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            booking_id INTEGER NOT NULL,
            folio_id INTEGER,
            posting_type VARCHAR(80) NOT NULL,
            folio_transaction_id INTEGER,
            amount NUMERIC(12, 2) DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'ETB',
            status VARCHAR(50) DEFAULT 'posted',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(property_code, business_date, booking_id, posting_type)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS business_date_locks (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            status VARCHAR(50) DEFAULT 'locked',
            locked_by VARCHAR(150),
            locked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            notes TEXT,
            UNIQUE(property_code, business_date)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS report_archive (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            report_key VARCHAR(120) NOT NULL,
            report_name VARCHAR(200) NOT NULL,
            report_payload JSONB,
            status VARCHAR(50) DEFAULT 'generated',
            generated_by VARCHAR(100),
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_night_audit_postings_date ON night_audit_postings(property_code, business_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_business_date_locks_date ON business_date_locks(property_code, business_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_archive_date ON report_archive(property_code, business_date)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_report_archive_date")
    op.execute("DROP INDEX IF EXISTS idx_business_date_locks_date")
    op.execute("DROP INDEX IF EXISTS idx_night_audit_postings_date")
