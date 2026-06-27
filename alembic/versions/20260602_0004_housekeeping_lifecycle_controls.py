"""Housekeeping room lifecycle controls.

Revision ID: 20260602_0004
Revises: 20260602_0003
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0004"
down_revision: Union[str, Sequence[str], None] = "20260602_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pms_roles (
            id SERIAL PRIMARY KEY,
            role_key VARCHAR(80) UNIQUE NOT NULL,
            role_name VARCHAR(150) NOT NULL,
            description TEXT,
            is_system_role BOOLEAN DEFAULT FALSE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pms_role_permissions (
            id SERIAL PRIMARY KEY,
            role_key VARCHAR(80) NOT NULL,
            permission_key VARCHAR(150) NOT NULL,
            allowed BOOLEAN DEFAULT TRUE,
            UNIQUE(role_key, permission_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS housekeeping_status (
            id SERIAL PRIMARY KEY,
            business_date DATE NOT NULL,
            property_code VARCHAR(20) NOT NULL,
            room_number VARCHAR(20) NOT NULL,
            hk_status VARCHAR(50) NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (business_date, property_code, room_number)
        )
        """
    )
    op.execute(
        """
        ALTER TABLE housekeeping_status
        ADD COLUMN IF NOT EXISTS note TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE housekeeping_status
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        ALTER TABLE housekeeping_status
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_housekeeping_status_day_room
        ON housekeeping_status (business_date, property_code, room_number)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_housekeeping_status_property_date_status
        ON housekeeping_status (property_code, business_date, hk_status)
        """
    )
    op.execute(
        """
        INSERT INTO pms_role_permissions (role_key, permission_key, allowed)
        VALUES
            ('general_manager', 'housekeeping.mark_cleaned', TRUE),
            ('general_manager', 'housekeeping.mark_inspected', TRUE),
            ('general_manager', 'housekeeping.room_status_override', TRUE),
            ('admin', 'housekeeping.mark_cleaned', TRUE),
            ('admin', 'housekeeping.mark_inspected', TRUE),
            ('admin', 'housekeeping.room_status_override', TRUE),
            ('housekeeping_supervisor', 'housekeeping.mark_cleaned', TRUE),
            ('housekeeping_supervisor', 'housekeeping.mark_inspected', TRUE),
            ('housekeeping_supervisor', 'housekeeping.room_status_override', TRUE)
        ON CONFLICT (role_key, permission_key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_housekeeping_status_property_date_status")
