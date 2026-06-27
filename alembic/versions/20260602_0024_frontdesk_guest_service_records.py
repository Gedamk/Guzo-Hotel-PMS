"""Persist Front Desk guest service tools.

Revision ID: 20260602_0024
Revises: 20260602_0023
Create Date: 2026-06-18
"""

from alembic import op


revision = "20260602_0024"
down_revision = "20260602_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS frontdesk_service_records (
            id SERIAL PRIMARY KEY,
            record_type VARCHAR(40) NOT NULL,
            property_code VARCHAR(20) NOT NULL,
            booking_id INTEGER NULL,
            reservation_reference VARCHAR(120) NULL,
            guest_name VARCHAR(180) NULL,
            room_number VARCHAR(50) NULL,
            status VARCHAR(40) NOT NULL DEFAULT 'open',
            priority VARCHAR(40) NOT NULL DEFAULT 'normal',
            assigned_to VARCHAR(150) NULL,
            created_by VARCHAR(150) NOT NULL DEFAULT 'frontdesk',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ NULL,
            notes TEXT NULL,
            task_key VARCHAR(120) NULL,
            title VARCHAR(180) NULL,
            scheduled_for TIMESTAMPTZ NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_frontdesk_service_records_property_type_status
        ON frontdesk_service_records (property_code, record_type, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_frontdesk_service_records_booking
        ON frontdesk_service_records (property_code, booking_id)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_frontdesk_service_records_task_key
        ON frontdesk_service_records (property_code, record_type, booking_id, task_key)
        WHERE task_key IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_frontdesk_service_records_task_key")
    op.execute("DROP INDEX IF EXISTS ix_frontdesk_service_records_booking")
    op.execute("DROP INDEX IF EXISTS ix_frontdesk_service_records_property_type_status")
    # Keep records on downgrade to avoid losing operational guest service history.
