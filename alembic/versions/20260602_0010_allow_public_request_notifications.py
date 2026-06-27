"""Allow public request notifications before booking conversion.

Revision ID: 20260602_0010
Revises: 20260602_0009
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0010"
down_revision: Union[str, Sequence[str], None] = "20260602_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER")
    op.execute("ALTER TABLE guest_notification_outbox ALTER COLUMN booking_id DROP NOT NULL")


def downgrade() -> None:
    pass
