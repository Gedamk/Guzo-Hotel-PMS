"""Add reservation guest count columns to bookings.

Revision ID: 20260602_0016
Revises: 20260602_0015
Create Date: 2026-06-06
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0016"
down_revision: Union[str, Sequence[str], None] = "20260602_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS nights INTEGER")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS adults INTEGER DEFAULT 1")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS children INTEGER DEFAULT 0")
    op.execute("UPDATE bookings SET adults = COALESCE(adults, 1)")
    op.execute("UPDATE bookings SET children = COALESCE(children, 0)")


def downgrade() -> None:
    # Preserve booking data and compatibility columns.
    pass
