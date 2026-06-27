"""PMS production control tables for Booking Hub, rates, payments, and audit.

Revision ID: 20260602_0001
Revises: None
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260602_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_plans (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            code VARCHAR(20) NOT NULL,
            name VARCHAR(150) NOT NULL,
            multiplier NUMERIC(8, 4) DEFAULT 1,
            requires_manager_approval BOOLEAN DEFAULT FALSE,
            cancellation_policy TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS room_type_rates (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            room_type VARCHAR(100) NOT NULL,
            base_rate_etb NUMERIC(12, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'ETB',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, room_type)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tax_service_rules (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            rule_name VARCHAR(120) NOT NULL,
            tax_percent NUMERIC(8, 4) DEFAULT 0.15,
            service_charge_percent NUMERIC(8, 4) DEFAULT 0.10,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, rule_name)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS season_rules (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            rule_name VARCHAR(120) NOT NULL,
            start_month INTEGER NOT NULL,
            end_month INTEGER NOT NULL,
            surcharge_percent NUMERIC(8, 4) DEFAULT 0.15,
            weekend_surcharge_percent NUMERIC(8, 4) DEFAULT 0.10,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS deposit_policies (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            rate_code VARCHAR(20) NOT NULL,
            deposit_percent NUMERIC(8, 4) DEFAULT 0.25,
            guarantee_required BOOLEAN DEFAULT TRUE,
            policy_text TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, rate_code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hotels (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(150) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            hotel_id INTEGER,
            property_code VARCHAR(20) NOT NULL,
            room_number VARCHAR(50) NOT NULL,
            room_type VARCHAR(100),
            floor INTEGER,
            status VARCHAR(50) DEFAULT 'in_service',
            is_occupied BOOLEAN DEFAULT FALSE,
            housekeeping_status VARCHAR(50) DEFAULT 'vacant_clean',
            hk_status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, room_number)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            confirmation_id VARCHAR(100),
            hotel_id INTEGER,
            property_code VARCHAR(20),
            guest_name VARCHAR(150),
            guest_email VARCHAR(150),
            guest_phone VARCHAR(50),
            room_number VARCHAR(50),
            room_type VARCHAR(100),
            check_in_date DATE,
            check_out_date DATE,
            nights INTEGER,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            booking_status VARCHAR(50),
            reservation_status VARCHAR(50),
            reservation_type VARCHAR(80),
            channel VARCHAR(80),
            source VARCHAR(80),
            payment_method VARCHAR(80),
            payment_status VARCHAR(50),
            currency VARCHAR(10) DEFAULT 'ETB',
            rate_per_night_etb NUMERIC(12, 2),
            total_amount NUMERIC(12, 2),
            total_revenue_etb NUMERIC(12, 2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    _ensure_existing_configuration_columns()
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public_booking_requests (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            source VARCHAR(50) DEFAULT 'chatbot',
            channel VARCHAR(50),
            guest_name VARCHAR(150) NOT NULL,
            guest_phone VARCHAR(50),
            guest_email VARCHAR(150),
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            room_type VARCHAR(100),
            reservation_type VARCHAR(50) DEFAULT 'individual',
            booking_status VARCHAR(50) DEFAULT 'pending_request',
            guarantee_type VARCHAR(50) DEFAULT 'non_guaranteed',
            deposit_status VARCHAR(50) DEFAULT 'pending',
            special_requests TEXT,
            notes TEXT,
            converted_booking_id INTEGER,
            converted_at TIMESTAMP,
            converted_by VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_booking_id INTEGER")
    op.execute("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_at TIMESTAMP")
    op.execute("ALTER TABLE public_booking_requests ADD COLUMN IF NOT EXISTS converted_by VARCHAR(150)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_requests (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            public_request_id INTEGER,
            booking_id INTEGER,
            guest_name VARCHAR(150),
            guest_email VARCHAR(150),
            guest_phone VARCHAR(50),
            amount_etb NUMERIC(12, 2) DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'ETB',
            token VARCHAR(160) UNIQUE NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            expires_at TIMESTAMP,
            created_by VARCHAR(150) DEFAULT 'booking_hub_staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_notification_outbox (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER,
            public_request_id INTEGER,
            property_code VARCHAR(50) NOT NULL,
            channel VARCHAR(50) NOT NULL,
            recipient TEXT,
            action VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            business_date DATE,
            status VARCHAR(50) NOT NULL DEFAULT 'queued',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE guest_notification_outbox ADD COLUMN IF NOT EXISTS public_request_id INTEGER")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS folios (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            booking_id INTEGER NOT NULL,
            guest_name VARCHAR(150) NOT NULL,
            currency VARCHAR(10) DEFAULT 'ETB',
            status VARCHAR(50) DEFAULT 'open',
            total_charges NUMERIC(12, 2) DEFAULT 0,
            total_payments NUMERIC(12, 2) DEFAULT 0,
            balance NUMERIC(12, 2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS total_charges NUMERIC(12, 2) DEFAULT 0")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS total_payments NUMERIC(12, 2) DEFAULT 0")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS balance NUMERIC(12, 2) DEFAULT 0")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open'")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            hotel_id INTEGER NULL,
            property_code VARCHAR(50) NULL,
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            entity_id INTEGER NULL,
            business_date DATE NULL,
            performed_by VARCHAR(100) NULL,
            details JSONB NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pms_audit_logs (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20),
            user_email VARCHAR(255),
            module VARCHAR(80),
            action VARCHAR(150),
            record_type VARCHAR(100),
            record_id VARCHAR(100),
            old_value JSONB,
            new_value JSONB,
            ip_address VARCHAR(80),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS confirmation_id VARCHAR(100)")
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS rate_per_night_etb NUMERIC(12, 2)")
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS total_revenue_etb NUMERIC(12, 2)")
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50)")
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS source VARCHAR(80)")
    op.execute("ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS property_code VARCHAR(20)")
    _seed_defaults()


def _ensure_existing_configuration_columns() -> None:
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS multiplier NUMERIC(8, 4) DEFAULT 1")
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS requires_manager_approval BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS cancellation_policy TEXT")
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE rate_plans ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE room_type_rates ADD COLUMN IF NOT EXISTS base_rate_etb NUMERIC(12, 2) DEFAULT 0")
    op.execute("ALTER TABLE room_type_rates ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ETB'")
    op.execute("ALTER TABLE room_type_rates ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE room_type_rates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE room_type_rates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE tax_service_rules ADD COLUMN IF NOT EXISTS tax_percent NUMERIC(8, 4) DEFAULT 0.15")
    op.execute("ALTER TABLE tax_service_rules ADD COLUMN IF NOT EXISTS service_charge_percent NUMERIC(8, 4) DEFAULT 0.10")
    op.execute("ALTER TABLE tax_service_rules ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE tax_service_rules ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE tax_service_rules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE season_rules ADD COLUMN IF NOT EXISTS surcharge_percent NUMERIC(8, 4) DEFAULT 0.15")
    op.execute("ALTER TABLE season_rules ADD COLUMN IF NOT EXISTS weekend_surcharge_percent NUMERIC(8, 4) DEFAULT 0.10")
    op.execute("ALTER TABLE season_rules ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE season_rules ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE season_rules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS deposit_percent NUMERIC(8, 4) DEFAULT 0.25")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS guarantee_required BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS policy_text TEXT")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE deposit_policies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")


def _seed_defaults() -> None:
    op.execute(
        """
        INSERT INTO rate_plans (property_code, code, name, multiplier, requires_manager_approval, cancellation_policy, is_active)
        VALUES
          ('DRE001', 'BAR', 'Best Available Rate', 1.0000, FALSE, 'Flexible cancellation until 18:00 hotel time one day before arrival; first night may apply after cutoff.', TRUE),
          ('DRE001', 'CORP', 'Corporate Preferred', 0.9000, FALSE, 'Corporate guarantee required; cancellation follows the approved account agreement.', TRUE),
          ('DRE001', 'GRP10', 'Group 10+ Rooms', 0.8500, TRUE, 'Group deposit and rooming-list cutoff required before final confirmation.', TRUE)
        ON CONFLICT (property_code, code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO room_type_rates (property_code, room_type, base_rate_etb, currency, is_active)
        VALUES
          ('DRE001', 'Standard', 5200.00, 'ETB', TRUE),
          ('DRE001', 'Deluxe', 6500.00, 'ETB', TRUE),
          ('DRE001', 'Twin', 5600.00, 'ETB', TRUE),
          ('DRE001', 'Family', 7200.00, 'ETB', TRUE),
          ('DRE001', 'Suite', 11000.00, 'ETB', TRUE)
        ON CONFLICT (property_code, room_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO tax_service_rules (property_code, rule_name, tax_percent, service_charge_percent, is_active)
        VALUES ('DRE001', 'Default Tax / Service', 0.1500, 0.1000, TRUE)
        ON CONFLICT (property_code, rule_name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO season_rules (property_code, rule_name, start_month, end_month, surcharge_percent, weekend_surcharge_percent, is_active)
        SELECT 'DRE001', 'High Season', 7, 12, 0.1500, 0.1000, TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM season_rules WHERE property_code = 'DRE001' AND rule_name = 'High Season'
        )
        """
    )
    op.execute(
        """
        INSERT INTO deposit_policies (property_code, rate_code, deposit_percent, guarantee_required, policy_text, is_active)
        VALUES
          ('DRE001', 'BAR', 0.2500, TRUE, 'Flexible cancellation until 18:00 hotel time one day before arrival; first night may apply after cutoff.', TRUE),
          ('DRE001', 'CORP', 0.0000, TRUE, 'Corporate guarantee required; cancellation follows the approved account agreement.', TRUE),
          ('DRE001', 'GRP10', 0.3000, TRUE, 'Group deposit and rooming-list cutoff required before final confirmation.', TRUE)
        ON CONFLICT (property_code, rate_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS deposit_policies")
    op.execute("DROP TABLE IF EXISTS season_rules")
    op.execute("DROP TABLE IF EXISTS tax_service_rules")
    op.execute("DROP TABLE IF EXISTS room_type_rates")
    op.execute("DROP TABLE IF EXISTS rate_plans")
    op.execute("DROP TABLE IF EXISTS payment_requests")
    op.execute("DROP TABLE IF EXISTS guest_notification_outbox")
    op.execute("DROP TABLE IF EXISTS public_booking_requests")
