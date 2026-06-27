"""Add guest feedback table for dashboard summary.

Revision ID: 20260602_0011
Revises: 20260602_0010
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0011"
down_revision: Union[str, Sequence[str], None] = "20260602_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_feedback (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            booking_id INTEGER,
            guest_name VARCHAR(150),
            rating NUMERIC(3, 2),
            feedback_source VARCHAR(50),
            comment TEXT,
            status VARCHAR(50) DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS booking_id INTEGER")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_name VARCHAR(150)")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2)")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS feedback_source VARCHAR(50)")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS comment TEXT")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'new'")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_guest_feedback_property_created
        ON guest_feedback (property_code, created_at DESC)
        """
    )


def downgrade() -> None:
    pass
