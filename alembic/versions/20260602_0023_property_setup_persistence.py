"""Persist Admin Property Setup properties.

Revision ID: 20260602_0023
Revises: 20260602_0022
Create Date: 2026-06-18
"""

from alembic import op


revision = "20260602_0023"
down_revision = "20260602_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hotel_properties (
            id SERIAL PRIMARY KEY,
            name VARCHAR(180) NOT NULL,
            property_code VARCHAR(20) NOT NULL UNIQUE,
            address TEXT NOT NULL DEFAULT '',
            city VARCHAR(120) NOT NULL DEFAULT '',
            country VARCHAR(120) NOT NULL DEFAULT '',
            timezone VARCHAR(100) NOT NULL DEFAULT 'Africa/Addis_Ababa',
            currency VARCHAR(10) NOT NULL DEFAULT 'ETB',
            phone VARCHAR(80) NOT NULL DEFAULT '',
            email VARCHAR(255) NOT NULL DEFAULT '',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            onboarding_status VARCHAR(40) NOT NULL DEFAULT 'not_started',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_hotel_properties_active ON hotel_properties (is_active)")
    op.execute(
        """
        INSERT INTO hotel_properties (
            name, property_code, address, city, country, timezone,
            currency, phone, email, is_active, onboarding_status
        )
        VALUES
          (
            'Dream Big Hotel', 'DRE001', 'Bole Road', 'Addis Ababa', 'Ethiopia',
            'Africa/Addis_Ababa', 'ETB', '+251 11 000 0000',
            'admin@dreambig.local', TRUE, 'complete'
          ),
          (
            'N&N Hotel', 'NN002', 'Airport District', 'Addis Ababa', 'Ethiopia',
            'Africa/Addis_Ababa', 'ETB', '+251 11 000 0001',
            'admin@nnhotel.local', TRUE, 'in_progress'
          )
        ON CONFLICT (property_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hotel_properties_active")
    # Keep property records on downgrade to avoid losing multi-property setup data.
