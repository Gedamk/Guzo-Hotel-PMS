"""Front Desk workflow persistence fields.

Revision ID: 20260602_0022
Revises: 20260602_0021
Create Date: 2026-06-14
"""

from alembic import op


revision = "20260602_0022"
down_revision = "20260602_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_status VARCHAR(40)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_started_at TIMESTAMP")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_priority VARCHAR(40)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_notes TEXT")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_removed_at TIMESTAMP")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS q_removed_by VARCHAR(150)")

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_generated_at TIMESTAMP")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_generated_by VARCHAR(150)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_signed BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_signed_at TIMESTAMP")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS registration_card_notes TEXT")

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_status VARCHAR(50)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_amount NUMERIC(12, 2)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_type VARCHAR(50)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_code VARCHAR(120)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_notes TEXT")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_recorded_by VARCHAR(150)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS authorization_recorded_at TIMESTAMP")

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_offered BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_accepted BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_declined BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_from_room_type VARCHAR(100)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_to_room_type VARCHAR(100)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_amount_per_night NUMERIC(12, 2)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_total_amount NUMERIC(12, 2)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_recorded_by VARCHAR(150)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS upsell_recorded_at TIMESTAMP")

    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_frontdesk_q ON bookings (property_code, q_status, q_priority)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_frontdesk_authorization ON bookings (property_code, authorization_status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bookings_frontdesk_authorization")
    op.execute("DROP INDEX IF EXISTS ix_bookings_frontdesk_q")
    # Keep additive workflow columns on downgrade to avoid losing operational audit context.
