"""Clarify room service status semantics.

Revision ID: 20260602_0006
Revises: 20260602_0005
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0006"
down_revision: Union[str, Sequence[str], None] = "20260602_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE housekeeping_status
        SET hk_status = 'service_in_progress',
            updated_at = CURRENT_TIMESTAMP
        WHERE hk_status = 'in_service'
          AND (
              LOWER(COALESCE(note, '')) LIKE '%clean%'
              OR LOWER(COALESCE(note, '')) LIKE '%progress%'
              OR LOWER(COALESCE(note, '')) LIKE '%attendant%'
          )
        """
    )


def downgrade() -> None:
    pass
