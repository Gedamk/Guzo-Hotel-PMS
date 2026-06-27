"""Add guest service recovery fields.

Revision ID: 20260602_0012
Revises: 20260602_0011
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0012"
down_revision: Union[str, Sequence[str], None] = "20260602_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(150)")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium'")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS recovery_action TEXT")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS follow_up_date DATE")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS resolution_notes TEXT")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_contacted BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS compensation_offered VARCHAR(50) DEFAULT 'none'")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_guest_feedback_status_priority
        ON guest_feedback (property_code, status, priority)
        """
    )


def downgrade() -> None:
    pass
