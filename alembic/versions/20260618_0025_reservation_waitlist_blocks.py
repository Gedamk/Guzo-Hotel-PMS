"""Persist reservation waitlist and group blocks.

Revision ID: 20260618_0025
Revises: 20260602_0024
Create Date: 2026-06-18
"""

from alembic import op


revision = "20260618_0025"
down_revision = "20260602_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reservation_waitlist (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            guest_name VARCHAR(180) NOT NULL,
            guest_email VARCHAR(255),
            guest_phone VARCHAR(80),
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            room_type VARCHAR(120) NOT NULL,
            rooms INTEGER NOT NULL DEFAULT 1,
            adults INTEGER NOT NULL DEFAULT 1,
            children INTEGER NOT NULL DEFAULT 0,
            rate_code VARCHAR(40) NOT NULL DEFAULT 'BAR',
            source VARCHAR(80) NOT NULL DEFAULT 'direct',
            notes TEXT,
            status VARCHAR(40) NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'available', 'converted', 'cancelled')),
            available_rooms INTEGER,
            converted_booking_id INTEGER,
            cancellation_reason TEXT,
            created_by VARCHAR(255) NOT NULL DEFAULT 'reservations',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            availability_checked_at TIMESTAMPTZ,
            converted_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            CHECK (check_out_date > check_in_date),
            CHECK (rooms >= 1),
            CHECK (adults >= 1),
            CHECK (children >= 0)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_reservation_waitlist_property_status
        ON reservation_waitlist (property_code, status, check_in_date)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reservation_blocks (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            block_name VARCHAR(180) NOT NULL,
            company_name VARCHAR(180),
            contact_name VARCHAR(180) NOT NULL,
            contact_email VARCHAR(255),
            contact_phone VARCHAR(80),
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            room_type VARCHAR(120) NOT NULL,
            rooms INTEGER NOT NULL DEFAULT 1,
            rate_code VARCHAR(40) NOT NULL DEFAULT 'GRP10',
            status VARCHAR(40) NOT NULL DEFAULT 'tentative'
                CHECK (status IN ('tentative', 'quoted', 'deposit_requested', 'confirmed', 'cancelled')),
            quoted_amount NUMERIC(14, 2),
            deposit_amount NUMERIC(14, 2),
            notes TEXT,
            cancellation_reason TEXT,
            created_by VARCHAR(255) NOT NULL DEFAULT 'reservations',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            quoted_at TIMESTAMPTZ,
            deposit_requested_at TIMESTAMPTZ,
            confirmed_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            CHECK (check_out_date > check_in_date),
            CHECK (rooms >= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_reservation_blocks_property_status
        ON reservation_blocks (property_code, status, check_in_date)
        """
    )


def downgrade() -> None:
    # Preserve operational reservation records on downgrade.
    op.execute("DROP INDEX IF EXISTS ix_reservation_blocks_property_status")
    op.execute("DROP INDEX IF EXISTS ix_reservation_waitlist_property_status")
