"""Seed Booking Hub permission aliases.

Revision ID: 20260602_0008
Revises: 20260602_0007
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0008"
down_revision: Union[str, Sequence[str], None] = "20260602_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_pms_role_permission'
                  AND conrelid = 'pms_role_permissions'::regclass
            )
            AND NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'pms_role_permissions_role_key_permission_key_key'
                  AND conrelid = 'pms_role_permissions'::regclass
            )
            THEN
                ALTER TABLE pms_role_permissions
                ADD CONSTRAINT uq_pms_role_permission UNIQUE (role_key, permission_key);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        INSERT INTO pms_role_permissions (role_key, permission_key, allowed)
        VALUES
            ('admin', 'booking.review_public_request', TRUE),
            ('admin', 'booking.reject_public_request', TRUE),
            ('admin', 'booking.request_deposit', TRUE),
            ('admin', 'booking.convert_public_request', TRUE),
            ('admin', 'admin.manage_rate_configuration', TRUE),
            ('general_manager', 'booking.review_public_request', TRUE),
            ('general_manager', 'booking.reject_public_request', TRUE),
            ('general_manager', 'booking.request_deposit', TRUE),
            ('general_manager', 'booking.convert_public_request', TRUE),
            ('general_manager', 'admin.manage_rate_configuration', TRUE),
            ('reservations_agent', 'booking.review_public_request', TRUE),
            ('reservations_agent', 'booking.reject_public_request', TRUE),
            ('reservations_agent', 'booking.request_deposit', TRUE),
            ('reservations_agent', 'booking.convert_public_request', TRUE),
            ('frontdesk_agent', 'booking.review_public_request', TRUE)
        ON CONFLICT (role_key, permission_key) DO NOTHING
        """
    )


def downgrade() -> None:
    pass
