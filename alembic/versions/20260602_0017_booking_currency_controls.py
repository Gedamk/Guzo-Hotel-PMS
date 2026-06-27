"""Add booking currency controls for folio and receipt accuracy.

Revision ID: 20260602_0017
Revises: 20260602_0016
Create Date: 2026-06-06
"""

from alembic import op


revision = "20260602_0017"
down_revision = "20260602_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ETB'")
    op.execute("UPDATE bookings SET currency = COALESCE(NULLIF(TRIM(currency), ''), 'ETB')")
    op.execute(
        """
        UPDATE bookings
        SET currency = UPPER(match.currency)
        FROM (
            SELECT id, (regexp_match(notes, 'Currency:\\s*([A-Za-z]{3})'))[1] AS currency
            FROM bookings
            WHERE notes ~* 'Currency:\\s*[A-Za-z]{3}'
        ) AS match
        WHERE bookings.id = match.id
          AND match.currency IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE folios
        SET currency = bookings.currency
        FROM bookings
        WHERE folios.booking_id = bookings.id
          AND folios.property_code = bookings.property_code
          AND bookings.currency IS NOT NULL
          AND UPPER(COALESCE(folios.currency, 'ETB')) <> UPPER(bookings.currency)
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_currency ON bookings(currency)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bookings_currency")
