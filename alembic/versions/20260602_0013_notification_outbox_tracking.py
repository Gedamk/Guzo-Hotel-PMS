"""Add notification outbox tracking fields.

Revision ID: 20260602_0013
Revises: 20260602_0012
Create Date: 2026-06-02
"""

from alembic import op


revision = "20260602_0013"
down_revision = "20260602_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS failure_reason TEXT")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0")
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ")
    op.execute("UPDATE guest_notification_outbox SET attempt_count = COALESCE(attempt_count, 0)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_guest_notification_outbox_delivery
        ON guest_notification_outbox (status, last_attempt_at, created_at)
        """
    )


def downgrade():
    op.drop_column("guest_notification_outbox", "last_attempt_at")
    op.drop_column("guest_notification_outbox", "attempt_count")
    op.drop_column("guest_notification_outbox", "failure_reason")
    op.drop_column("guest_notification_outbox", "failed_at")
    op.drop_column("guest_notification_outbox", "sent_at")
