"""Add guest profile and communication queue schema.

Revision ID: 20260602_0014
Revises: 20260602_0013
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0014"
down_revision: Union[str, Sequence[str], None] = "20260602_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_profiles (
            id SERIAL PRIMARY KEY,
            guest_id VARCHAR(80) UNIQUE NOT NULL,
            property_code VARCHAR(20) NOT NULL,
            guest_name VARCHAR(150) NOT NULL,
            phone VARCHAR(80),
            email VARCHAR(255),
            nationality VARCHAR(100),
            id_passport_placeholder VARCHAR(160),
            vip_flag BOOLEAN DEFAULT FALSE,
            preferences JSONB DEFAULT '{}'::jsonb,
            stay_history JSONB DEFAULT '[]'::jsonb,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS phone VARCHAR(80)")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS email VARCHAR(255)")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS nationality VARCHAR(100)")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS id_passport_placeholder VARCHAR(160)")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS vip_flag BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS stay_history JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS notes TEXT")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE guest_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ")

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)")
    op.execute("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER")
    op.execute("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER")
    op.execute("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)")

    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ")
    op.execute("UPDATE guest_notification_outbox SET status = 'skipped' WHERE status = 'pending_contact_review'")
    op.execute("UPDATE guest_notification_outbox SET attempt_count = COALESCE(attempt_count, 0)")
    op.execute("UPDATE guest_notification_outbox SET retry_count = COALESCE(retry_count, attempt_count, 0)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manager_alerts (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            alert_type VARCHAR(100) NOT NULL,
            severity VARCHAR(30) DEFAULT 'warning',
            message TEXT NOT NULL,
            guest_profile_id INTEGER,
            guest_id VARCHAR(80),
            booking_id INTEGER,
            public_request_id INTEGER,
            business_date DATE,
            status VARCHAR(50) DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_profiles_guest_id ON guest_profiles (guest_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_profiles_property_code ON guest_profiles (property_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_profiles_email ON guest_profiles (LOWER(email))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_profiles_phone ON guest_profiles (phone)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_guest_profile ON bookings (guest_profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_guest_id ON bookings (guest_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_public_booking_requests_guest_profile ON public_booking_requests (guest_profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_folios_guest_profile ON folios (guest_profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_feedback_guest_profile ON guest_feedback (guest_profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_notification_outbox_guest_profile ON guest_notification_outbox (guest_profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_notification_outbox_status ON guest_notification_outbox (status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_notification_outbox_booking ON guest_notification_outbox (booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_manager_alerts_status ON manager_alerts (property_code, status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_manager_alerts_booking ON manager_alerts (booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_manager_alerts_guest_profile ON manager_alerts (guest_profile_id)")


def downgrade() -> None:
    # Preserve guest, booking, folio, feedback, notification, and alert records.
    pass
