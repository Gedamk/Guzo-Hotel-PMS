"""Sensitive action role permissions.

Revision ID: 20260602_0007
Revises: 20260602_0006
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0007"
down_revision: Union[str, Sequence[str], None] = "20260602_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO pms_role_permissions (role_key, permission_key, allowed)
        VALUES
            ('general_manager', 'reservations.review_booking_request', TRUE),
            ('general_manager', 'reservations.convert_booking', TRUE),
            ('general_manager', 'finance.post_charge', TRUE),
            ('admin', 'reservations.review_booking_request', TRUE),
            ('admin', 'reservations.convert_booking', TRUE),
            ('admin', 'finance.post_charge', TRUE),
            ('reservations_agent', 'reservations.review_booking_request', TRUE),
            ('reservations_agent', 'reservations.convert_booking', TRUE),
            ('finance_cashier', 'finance.post_charge', TRUE)
        ON CONFLICT (role_key, permission_key) DO NOTHING
        """
    )


def downgrade() -> None:
    pass
