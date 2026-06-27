"""Add PMS authentication foundation columns.

Revision ID: 20260602_0015
Revises: 20260602_0014
Create Date: 2026-06-06
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0015"
down_revision: Union[str, Sequence[str], None] = "20260602_0014"
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
        CREATE TABLE IF NOT EXISTS pms_users (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            role_key VARCHAR(80) NOT NULL,
            property_code VARCHAR(20),
            is_active BOOLEAN DEFAULT TRUE,
            password_hash TEXT,
            last_login_at TIMESTAMP,
            disabled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMP")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS property_code VARCHAR(20)")
    op.execute("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("UPDATE pms_users SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)")
    op.execute("UPDATE pms_users SET is_active = TRUE WHERE is_active IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pms_users_email ON pms_users (LOWER(email))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pms_users_property_role ON pms_users (property_code, role_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pms_users_active ON pms_users (is_active)")


def downgrade() -> None:
    # Preserve users and credentials on downgrade.
    pass
