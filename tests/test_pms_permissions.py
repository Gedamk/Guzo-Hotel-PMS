from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "TEST_DATABASE_URL is required for PMS permission regression tests. "
        "Refusing to run against development, demo, pilot, or production data.",
        returncode=2,
    )

TEST_SCHEMA = f"pms_permission_qa_{uuid4().hex[:12]}"
PROPERTY_CODE = "DRE001"
BUSINESS_DATE = "2026-06-02"
ADMIN_EMAIL = "admin@guzo.local"
RESERVATION_MANAGER_EMAIL = "reservation.manager@guzo.local"
RESERVATIONS_EMAIL = "reservations@guzo.local"
FRONT_DESK_AGENT_EMAIL = "front.desk@guzo.local"
FRONTDESK_EMAIL = "frontdesk@guzo.local"
HOUSEKEEPING_EMAIL = "housekeeping@guzo.local"
ATTENDANT_EMAIL = "attendant@guzo.local"
FINANCE_EMAIL = "finance@guzo.local"
FINANCE_MANAGER_EMAIL = "finance.manager@guzo.local"
NIGHT_AUDIT_EMAIL = "nightaudit@guzo.local"


_test_engine = None
_TestingSessionLocal: sessionmaker[Session] | None = None


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _make_test_engine():
    url = make_url(TEST_DATABASE_URL)
    if url.get_backend_name() != "postgresql":
        pytest.exit(
            "TEST_DATABASE_URL must point to PostgreSQL so the permission tests match production SQL behavior.",
            returncode=2,
        )

    admin_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with admin_engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {_quote_ident(TEST_SCHEMA)}"))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _set_test_schema(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {_quote_ident(TEST_SCHEMA)}")
        cursor.close()

    return engine


def _drop_test_schema() -> None:
    admin_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with admin_engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {_quote_ident(TEST_SCHEMA)} CASCADE"))
    admin_engine.dispose()


def _override_get_db():
    if _TestingSessionLocal is None:
        raise RuntimeError("Permission regression test database was not initialized.")
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


from guzo_backend import dependencies as shared_dependencies  # noqa: E402
from guzo_backend.api.public_booking_requests_api import ensure_public_booking_requests_table  # noqa: E402
from guzo_backend.core import postgres_db  # noqa: E402
from guzo_backend.main import app  # noqa: E402
from guzo_backend.services.notification_delivery_service import EmailMessagePayload, process_email_outbox  # noqa: E402
from guzo_backend.services.pms_auth_service import hash_password  # noqa: E402
from guzo_backend.services.pms_security_service import ensure_pms_security_tables  # noqa: E402


def _execute_schema(sql: str) -> None:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(text(sql))
        db.commit()


def _create_qa_tables() -> None:
    _execute_schema(
        """
        CREATE TABLE hotels (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(150) NOT NULL
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE bookings (
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
            channel VARCHAR(80),
            source VARCHAR(80),
            payment_method VARCHAR(80),
            payment_status VARCHAR(50),
            currency VARCHAR(10) DEFAULT 'ETB',
            rate_per_night_etb NUMERIC(12, 2),
            total_amount NUMERIC(12, 2),
            total_revenue_etb NUMERIC(12, 2),
            notes TEXT,
            q_status VARCHAR(40),
            q_started_at TIMESTAMP,
            q_priority VARCHAR(40),
            q_notes TEXT,
            q_removed_at TIMESTAMP,
            q_removed_by VARCHAR(150),
            registration_card_generated_at TIMESTAMP,
            registration_card_generated_by VARCHAR(150),
            registration_card_signed BOOLEAN DEFAULT FALSE,
            registration_card_signed_at TIMESTAMP,
            registration_card_notes TEXT,
            authorization_status VARCHAR(50),
            authorization_amount NUMERIC(12, 2),
            authorization_type VARCHAR(50),
            authorization_code VARCHAR(120),
            authorization_notes TEXT,
            authorization_recorded_by VARCHAR(150),
            authorization_recorded_at TIMESTAMP,
            upsell_offered BOOLEAN DEFAULT FALSE,
            upsell_accepted BOOLEAN DEFAULT FALSE,
            upsell_declined BOOLEAN DEFAULT FALSE,
            upsell_from_room_type VARCHAR(100),
            upsell_to_room_type VARCHAR(100),
            upsell_amount_per_night NUMERIC(12, 2),
            upsell_total_amount NUMERIC(12, 2),
            upsell_recorded_by VARCHAR(150),
            upsell_recorded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE housekeeping_status (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            room_number VARCHAR(50) NOT NULL,
            business_date DATE,
            room_type VARCHAR(100),
            floor INTEGER,
            hk_status VARCHAR(50),
            front_office_status VARCHAR(50),
            guest_name VARCHAR(150),
            assigned_to VARCHAR(150),
            note TEXT,
            updated_by VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (business_date, property_code, room_number)
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE rooms (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            room_number VARCHAR(50) NOT NULL,
            room_type VARCHAR(100),
            floor INTEGER,
            is_occupied BOOLEAN DEFAULT FALSE,
            hk_status VARCHAR(50),
            status VARCHAR(50) DEFAULT 'in_service',
            housekeeping_status VARCHAR(50) DEFAULT 'vacant_clean'
        )
        """
    )
    _execute_schema(
        """
        INSERT INTO rooms (property_code, room_number, room_type, floor, is_occupied, housekeeping_status)
        VALUES
          ('DRE001', 'QA-101', 'Standard Room', 1, FALSE, 'vacant_clean'),
          ('DRE001', 'QA-102', 'Standard Room', 1, FALSE, 'vacant_dirty'),
          ('DRE001', 'QA-103', 'Standard Room', 1, FALSE, 'vacant_clean')
        """
    )
    _execute_schema(
        """
        CREATE TABLE folios (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            booking_id INTEGER NOT NULL,
            guest_name VARCHAR(150) NOT NULL,
            currency VARCHAR(10) DEFAULT 'ETB',
            status VARCHAR(50) DEFAULT 'open',
            total_charges NUMERIC(12, 2) DEFAULT 0,
            total_payments NUMERIC(12, 2) DEFAULT 0,
            balance NUMERIC(12, 2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE folio_transactions (
            id SERIAL PRIMARY KEY,
            folio_id INTEGER NOT NULL,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            txn_type VARCHAR(50) NOT NULL,
            category VARCHAR(80),
            description TEXT,
            amount NUMERIC(12, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'ETB',
            booking_id INTEGER,
            payment_method VARCHAR(80),
            reference VARCHAR(160),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE ingredients (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            name VARCHAR(150) NOT NULL,
            category VARCHAR(80),
            unit VARCHAR(20) NOT NULL,
            purchase_price NUMERIC(10, 2) NOT NULL,
            cost_per_unit NUMERIC(10, 4) NOT NULL,
            last_purchase_price NUMERIC(10, 2),
            average_cost NUMERIC(10, 4),
            supplier_id INTEGER,
            supplier_name VARCHAR(150),
            reorder_level NUMERIC(12, 3),
            expiry_date DATE,
            storage_location VARCHAR(120),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE recipes (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            name VARCHAR(150) NOT NULL,
            outlet_name VARCHAR(150),
            selling_price NUMERIC(10, 2) NOT NULL,
            total_cost NUMERIC(10, 2) DEFAULT 0,
            food_cost_percentage NUMERIC(10, 2) DEFAULT 0,
            target_cost_percentage NUMERIC(10, 2),
            profit_margin NUMERIC(10, 2),
            approval_status VARCHAR(40) DEFAULT 'draft',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            quantity_used NUMERIC(10, 3) NOT NULL,
            cost_used NUMERIC(10, 2) NOT NULL
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE food_cost_alerts (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            alert_type VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            severity VARCHAR(20) DEFAULT 'medium',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE inventory_movements (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150) NOT NULL,
            movement_type VARCHAR(50) NOT NULL,
            quantity NUMERIC(12, 3) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            unit_cost NUMERIC(12, 2),
            stock_value NUMERIC(12, 2),
            reference VARCHAR(160),
            notes TEXT,
            created_by VARCHAR(150) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE pos_sales (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            outlet_name VARCHAR(150) NOT NULL,
            menu_item_name VARCHAR(150) NOT NULL,
            quantity_sold NUMERIC(12, 3) NOT NULL,
            selling_price NUMERIC(12, 2) NOT NULL,
            total_revenue NUMERIC(12, 2) NOT NULL,
            tax_amount NUMERIC(12, 2),
            service_charge_amount NUMERIC(12, 2),
            payment_method VARCHAR(80),
            room_charge_booking_id INTEGER,
            folio_transaction_id INTEGER,
            business_date VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE tax_service_rules (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            rule_name VARCHAR(120) NOT NULL,
            tax_percent NUMERIC(8, 4) DEFAULT 0,
            service_charge_percent NUMERIC(8, 4) DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )
    _execute_schema(
        """
        INSERT INTO tax_service_rules (
            property_code, rule_name, tax_percent, service_charge_percent, is_active
        )
        VALUES ('DRE001', 'QA Tax / Service', 0.1500, 0.1000, TRUE)
        """
    )
    _execute_schema(
        """
        CREATE TABLE audit_logs (
            id SERIAL PRIMARY KEY,
            action VARCHAR(120) NOT NULL,
            entity_type VARCHAR(120),
            entity_id INTEGER,
            hotel_id INTEGER,
            property_code VARCHAR(20),
            business_date DATE,
            performed_by VARCHAR(150),
            details JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    _execute_schema(
        """
        CREATE TABLE finance_transactions (
            id BIGSERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            business_date DATE NOT NULL,
            folio_id BIGINT,
            booking_id BIGINT,
            account_reference VARCHAR(180),
            transaction_type VARCHAR(30) NOT NULL,
            amount NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
            currency VARCHAR(10) NOT NULL,
            direction VARCHAR(10) NOT NULL CHECK (direction IN ('debit', 'credit')),
            payment_method VARCHAR(80),
            reference VARCHAR(255),
            source_document_type VARCHAR(80),
            source_document_id VARCHAR(120),
            reversal_of_transaction_id BIGINT REFERENCES finance_transactions(id),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            idempotency_key VARCHAR(180) NOT NULL,
            audit_reference VARCHAR(120) NOT NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE (property_code, idempotency_key)
        );
        CREATE UNIQUE INDEX uq_finance_transaction_reversal_test
          ON finance_transactions(reversal_of_transaction_id)
          WHERE reversal_of_transaction_id IS NOT NULL;
        CREATE OR REPLACE FUNCTION prevent_finance_transaction_mutation_test()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'finance_transactions is immutable; post a reversal instead';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER finance_transactions_immutable_update_test
          BEFORE UPDATE ON finance_transactions
          FOR EACH ROW EXECUTE FUNCTION prevent_finance_transaction_mutation_test();
        CREATE TRIGGER finance_transactions_immutable_delete_test
          BEFORE DELETE ON finance_transactions
          FOR EACH ROW EXECUTE FUNCTION prevent_finance_transaction_mutation_test();
        """
    )
    _execute_schema(
        """
        CREATE TABLE cashier_sessions (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, business_date DATE NOT NULL,
          cashier_name VARCHAR(180) NOT NULL, assigned_user_email VARCHAR(255), opened_by VARCHAR(255),
          opening_float NUMERIC(18,2) NOT NULL DEFAULT 0, currency VARCHAR(10) NOT NULL DEFAULT 'ETB',
          cash NUMERIC(18,2) NOT NULL DEFAULT 0, card NUMERIC(18,2) NOT NULL DEFAULT 0,
          bank_transfer NUMERIC(18,2) NOT NULL DEFAULT 0, mobile_money NUMERIC(18,2) NOT NULL DEFAULT 0,
          unassigned NUMERIC(18,2) NOT NULL DEFAULT 0, actual_cash NUMERIC(18,2) NOT NULL DEFAULT 0,
          actual_card NUMERIC(18,2) NOT NULL DEFAULT 0, actual_bank_transfer NUMERIC(18,2) NOT NULL DEFAULT 0,
          actual_mobile_money NUMERIC(18,2) NOT NULL DEFAULT 0, actual_unassigned NUMERIC(18,2) NOT NULL DEFAULT 0,
          expected_total NUMERIC(18,2) NOT NULL DEFAULT 0, declared_total NUMERIC(18,2) NOT NULL DEFAULT 0,
          variance NUMERIC(18,2) NOT NULL DEFAULT 0, status VARCHAR(30) NOT NULL DEFAULT 'open', notes TEXT,
          opened_at TIMESTAMPTZ DEFAULT NOW(), declared_at TIMESTAMPTZ, approval_requested_at TIMESTAMPTZ,
          approved_at TIMESTAMPTZ, closed_at TIMESTAMPTZ, closed_by VARCHAR(255),
          manager_approved_by VARCHAR(255), manager_approval_reason TEXT, closure_report JSONB DEFAULT '{}'::jsonb
        );
        CREATE UNIQUE INDEX uq_cashier_active_assignment_test
          ON cashier_sessions(property_code,business_date,assigned_user_email) WHERE status <> 'closed';
        ALTER TABLE finance_transactions ADD COLUMN cashier_session_id BIGINT REFERENCES cashier_sessions(id);
        """
    )
    _execute_schema(
        """
        ALTER TABLE folios ADD COLUMN transferred_to TEXT;
        ALTER TABLE folios ADD COLUMN transfer_reason TEXT;
        ALTER TABLE folios ADD COLUMN transferred_at TIMESTAMPTZ;
        CREATE TABLE ar_company_accounts (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, company_name VARCHAR(180) NOT NULL,
          account_code VARCHAR(60) NOT NULL, billing_contact VARCHAR(180), email VARCHAR(255), phone VARCHAR(80),
          address TEXT, tax_id VARCHAR(100), credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0,
          current_balance NUMERIC(18,2) NOT NULL DEFAULT 0, status VARCHAR(20) NOT NULL DEFAULT 'active',
          payment_terms INTEGER NOT NULL DEFAULT 30, allow_direct_bill BOOLEAN NOT NULL DEFAULT TRUE,
          created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE(property_code,account_code)
        );
        CREATE TABLE ar_invoices (
          id BIGSERIAL PRIMARY KEY, invoice_number VARCHAR(80) NOT NULL, property_code VARCHAR(20) NOT NULL,
          company_account_id BIGINT NOT NULL REFERENCES ar_company_accounts(id), folio_id BIGINT, booking_id BIGINT,
          guest_reference VARCHAR(255), issue_date DATE NOT NULL, due_date DATE NOT NULL, subtotal NUMERIC(18,2) NOT NULL,
          tax NUMERIC(18,2) NOT NULL DEFAULT 0, total NUMERIC(18,2) NOT NULL, balance_due NUMERIC(18,2) NOT NULL,
          status VARCHAR(30) NOT NULL, transfer_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),
          override_reason TEXT, created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), voided_at TIMESTAMPTZ,
          UNIQUE(property_code,invoice_number), UNIQUE(property_code,folio_id)
        );
        CREATE TABLE ar_invoice_sources (id BIGSERIAL PRIMARY KEY,property_code VARCHAR(20) NOT NULL,invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id),finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),source_type VARCHAR(50) NOT NULL,amount NUMERIC(18,2) NOT NULL,created_at TIMESTAMPTZ DEFAULT NOW());
        CREATE TABLE ar_payments (id BIGSERIAL PRIMARY KEY,property_code VARCHAR(20) NOT NULL,company_account_id BIGINT NOT NULL REFERENCES ar_company_accounts(id),business_date DATE NOT NULL,amount NUMERIC(18,2) NOT NULL,currency VARCHAR(10) NOT NULL,payment_method VARCHAR(80) NOT NULL,reference VARCHAR(255),channel VARCHAR(30) NOT NULL,allocated_amount NUMERIC(18,2) DEFAULT 0,unapplied_amount NUMERIC(18,2) DEFAULT 0,finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),cashier_session_id BIGINT REFERENCES cashier_sessions(id),idempotency_key VARCHAR(180) NOT NULL,created_by VARCHAR(255) NOT NULL,created_at TIMESTAMPTZ DEFAULT NOW(),UNIQUE(property_code,idempotency_key));
        CREATE TABLE ar_payment_allocations (id BIGSERIAL PRIMARY KEY,property_code VARCHAR(20) NOT NULL,payment_id BIGINT NOT NULL REFERENCES ar_payments(id),invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id),amount NUMERIC(18,2) NOT NULL,created_at TIMESTAMPTZ DEFAULT NOW(),UNIQUE(payment_id,invoice_id));
        CREATE TABLE ar_adjustments (id BIGSERIAL PRIMARY KEY,property_code VARCHAR(20) NOT NULL,invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id),amount NUMERIC(18,2) NOT NULL,direction VARCHAR(10) NOT NULL,reason TEXT NOT NULL,finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),created_by VARCHAR(255) NOT NULL,created_at TIMESTAMPTZ DEFAULT NOW());
        """
    )
    _execute_schema(
        """
        CREATE TABLE deposit_accounts (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, booking_id BIGINT,
          public_request_id BIGINT, payment_request_id BIGINT, folio_id BIGINT, business_date DATE NOT NULL,
          required_amount NUMERIC(18,2) NOT NULL, requested_amount NUMERIC(18,2) NOT NULL,
          paid_amount NUMERIC(18,2) NOT NULL DEFAULT 0, allocated_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
          transferred_amount NUMERIC(18,2) NOT NULL DEFAULT 0, refunded_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
          forfeited_amount NUMERIC(18,2) NOT NULL DEFAULT 0, currency VARCHAR(10) NOT NULL DEFAULT 'ETB',
          refundable BOOLEAN NOT NULL DEFAULT TRUE, status VARCHAR(30) NOT NULL DEFAULT 'requested',
          payment_method VARCHAR(80), reference VARCHAR(255), created_by VARCHAR(255) NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now(),
          UNIQUE(property_code, booking_id)
        );
        CREATE TABLE deposit_events (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL,
          deposit_account_id BIGINT NOT NULL REFERENCES deposit_accounts(id), event_type VARCHAR(30) NOT NULL,
          amount NUMERIC(18,2) NOT NULL, currency VARCHAR(10) NOT NULL, payment_method VARCHAR(80),
          reference VARCHAR(255), finance_transaction_id BIGINT REFERENCES finance_transactions(id),
          idempotency_key VARCHAR(180) NOT NULL, audit_reference VARCHAR(120) NOT NULL,
          created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ DEFAULT now(), metadata_json JSONB DEFAULT '{}'::jsonb,
          UNIQUE(property_code, idempotency_key)
        );
        CREATE TABLE payment_batches (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, business_date DATE NOT NULL,
          booking_id BIGINT, folio_id BIGINT, account_reference VARCHAR(180), requested_amount NUMERIC(18,2) NOT NULL,
          received_amount NUMERIC(18,2) NOT NULL, overpayment_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
          currency VARCHAR(10) NOT NULL, status VARCHAR(30) NOT NULL, reference VARCHAR(255),
          idempotency_key VARCHAR(180) NOT NULL, created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ DEFAULT now(),
          UNIQUE(property_code, idempotency_key)
        );
        CREATE TABLE payment_allocations (
          id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL,
          payment_batch_id BIGINT NOT NULL REFERENCES payment_batches(id), payment_method VARCHAR(80) NOT NULL,
          amount NUMERIC(18,2) NOT NULL, reference VARCHAR(255),
          finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id), folio_transaction_id BIGINT,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    _execute_schema(
        """
        INSERT INTO hotels (property_code, name)
        VALUES
          ('DRE001', 'Dream Big Hotel'),
          ('NN002', 'N&N Hotel'),
          ('XXX001', 'XXX Hotel & Resort')
        """
    )

    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        ensure_public_booking_requests_table(db)
        ensure_pms_security_tables(db, PROPERTY_CODE)
        db.commit()


@pytest.fixture(scope="module", autouse=True)
def isolated_permission_database():
    global _test_engine, _TestingSessionLocal
    _test_engine = _make_test_engine()
    _TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
    app.dependency_overrides[postgres_db.get_db] = _override_get_db
    app.dependency_overrides[shared_dependencies.get_db] = _override_get_db
    try:
        _create_qa_tables()
        yield
    finally:
        app.dependency_overrides.pop(postgres_db.get_db, None)
        app.dependency_overrides.pop(shared_dependencies.get_db, None)
        if _test_engine is not None:
            _test_engine.dispose()
        _drop_test_schema()


@pytest.fixture()
def client(isolated_permission_database):
    with TestClient(app) as test_client:
        yield test_client


def _headers(email: str) -> dict[str, str]:
    return {"X-PMS-User-Email": email}


def _db_scalar(sql: str, params: dict | None = None):
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        return db.execute(text(sql), params or {}).scalar()


def _count_denied(permission_key: str, user_email: str) -> int:
    return int(
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE action = 'permission_denied'
              AND record_type = 'pms_permission'
              AND record_id = :permission_key
              AND LOWER(user_email) = LOWER(:user_email)
            """,
            {"permission_key": permission_key, "user_email": user_email},
        )
        or 0
    )


def _count_audit_action(action: str, booking_id: int) -> int:
    return int(
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE action = :action
              AND record_type = 'booking'
              AND record_id = :booking_id
            """,
            {"action": action, "booking_id": str(booking_id)},
        )
        or 0
    )


def _count_blocked_public_request_conversion(user_email: str) -> int:
    return int(
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE action = 'public_request_conversion_blocked_unauthorized'
              AND record_type = 'public_booking_request'
              AND LOWER(user_email) = LOWER(:user_email)
            """,
            {"user_email": user_email},
        )
        or 0
    )


def _assert_permission_denied(response, permission_key: str, user_email: str) -> None:
    assert response.status_code == 403, response.text
    detail = str(response.json().get("detail", ""))
    assert "Permission denied" in detail
    assert permission_key in detail
    assert _count_denied(permission_key, user_email) >= 1


def _assert_public_request_conversion_denied(response, user_email: str) -> None:
    assert response.status_code == 403
    detail = str(response.json().get("detail", ""))
    assert "Permission denied" in detail
    assert "reservation_manager" in detail
    assert "front_desk_agent" in detail
    assert "admin" in detail
    assert _count_blocked_public_request_conversion(user_email) >= 1


def _assert_authorized_reaches_normal_path(response, permission_key: str) -> None:
    assert response.status_code != 403, response.text
    assert permission_key not in response.text


def _seed_public_booking_request() -> int:
    today = date.fromisoformat(BUSINESS_DATE)
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO public_booking_requests (
                    property_code, source, channel, guest_name, guest_email,
                    check_in_date, check_out_date, adults, children, room_type,
                    reservation_type, booking_status, guarantee_type, deposit_status, notes
                )
                VALUES (
                    :property_code, 'pytest', 'pytest', :guest_name, :guest_email,
                    :check_in_date, :check_out_date, 1, 0, 'Standard Room',
                    'individual', 'pending_request', 'non_guaranteed', 'pending', 'permission regression seed'
                )
                RETURNING id
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "guest_name": f"Permission QA {uuid4()}",
                "guest_email": f"permission-{uuid4()}@example.test",
                "check_in_date": today,
                "check_out_date": today + timedelta(days=1),
            },
        ).first()
        db.commit()
        return int(row.id)


def _seed_booking(
    status: str = "confirmed",
    *,
    room_number: str = "QA-101",
    payment_status: str = "pending",
    total_amount: float = 100,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
) -> int:
    today = date.fromisoformat(check_in_date or BUSINESS_DATE)
    departure = date.fromisoformat(check_out_date) if check_out_date else today + timedelta(days=1)
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        hotel_id = db.execute(
            text("SELECT id FROM hotels WHERE property_code = :property_code LIMIT 1"),
            {"property_code": PROPERTY_CODE},
        ).scalar()
        row = db.execute(
            text(
                """
                INSERT INTO bookings (
                    confirmation_id, hotel_id, guest_name, guest_email, guest_phone, property_code,
                    room_number, room_type, check_in_date, check_out_date, booking_status,
                    channel, source, total_amount, total_revenue_etb, payment_status, notes
                )
                VALUES (
                    :confirmation_id, :hotel_id, :guest_name, :guest_email, :guest_phone, :property_code,
                    :room_number, 'Standard Room', :check_in_date, :check_out_date, :booking_status,
                    'pytest', 'pytest', :total_amount, :total_amount, :payment_status, 'permission regression seed'
                )
                RETURNING id
                """
            ),
            {
                "confirmation_id": f"QA-{uuid4()}",
                "hotel_id": hotel_id,
                "guest_name": f"Permission QA {uuid4()}",
                "guest_email": f"guest-{uuid4()}@example.test",
                "guest_phone": "251900000000",
                "property_code": PROPERTY_CODE,
                "room_number": room_number,
                "check_in_date": today,
                "check_out_date": departure,
                "booking_status": status,
                "payment_status": payment_status,
                "total_amount": total_amount,
            },
        ).first()
        db.commit()
        return int(row.id)


def _seed_admin_user() -> int:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES (:full_name, :email, 'read_only_owner', :property_code, TRUE)
                RETURNING id
                """
            ),
            {
                "full_name": "Permission QA User",
                "email": f"permission-{uuid4()}@example.test",
                "property_code": PROPERTY_CODE,
            },
        ).first()
        db.commit()
        return int(row.id)


def _seed_auth_user(
    *,
    email: str,
    password: str,
    role_key: str,
    is_active: bool = True,
    property_code: str = PROPERTY_CODE,
) -> None:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        ensure_pms_security_tables(db, property_code)
        db.execute(text("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS password_hash TEXT"))
        db.execute(text("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"))
        db.execute(text("ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMP"))
        db.execute(
            text(
                """
                INSERT INTO pms_users (
                    full_name, email, role_key, property_code, is_active, password_hash, updated_at
                )
                VALUES (
                    :full_name, :email, :role_key, :property_code, :is_active, :password_hash, CURRENT_TIMESTAMP
                )
                ON CONFLICT (email)
                DO UPDATE SET
                    role_key = EXCLUDED.role_key,
                    property_code = EXCLUDED.property_code,
                    is_active = EXCLUDED.is_active,
                    password_hash = EXCLUDED.password_hash,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "full_name": f"Auth QA {role_key}",
                "email": email,
                "role_key": role_key,
                "property_code": property_code,
                "is_active": is_active,
                "password_hash": hash_password(password),
            },
        )
        db.commit()


def _login_token(client, email: str, password: str = "Password123!") -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password, "property_code": PROPERTY_CODE},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _set_room_status(room_number: str, hk_status: str, is_occupied: bool = False) -> None:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE rooms
                SET housekeeping_status = :hk_status,
                    hk_status = :hk_status,
                    is_occupied = :is_occupied
                WHERE property_code = :property_code
                  AND room_number = :room_number
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "room_number": room_number,
                "hk_status": hk_status,
                "is_occupied": is_occupied,
            },
        )
        db.execute(
            text(
                """
                INSERT INTO housekeeping_status (
                    business_date, property_code, room_number, hk_status, note
                )
                VALUES (:business_date, :property_code, :room_number, :hk_status, 'permission lifecycle seed')
                ON CONFLICT (business_date, property_code, room_number)
                DO UPDATE SET hk_status = EXCLUDED.hk_status
                """
            ),
            {
                "business_date": BUSINESS_DATE,
                "property_code": PROPERTY_CODE,
                "room_number": room_number,
                "hk_status": hk_status,
            },
        )
        db.commit()


def _seed_folio(booking_id: int, *, balance: float = 0, currency: str = "ETB") -> int:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO folios (
                    property_code, booking_id, guest_name, currency, status,
                    total_charges, total_payments, balance
                )
                VALUES (
                    :property_code, :booking_id, 'Permission QA Guest', :currency, 'open',
                    :charges, :payments, :balance
                )
                RETURNING id
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "booking_id": booking_id,
                "currency": currency,
                "charges": max(balance, 0),
                "payments": 0,
                "balance": balance,
            },
        ).first()
        db.commit()
        return int(row.id)


def _seed_folio_transaction(
    folio_id: int,
    booking_id: int,
    txn_type: str,
    amount: float,
    *,
    category: str = "room",
    description: str = "permission regression transaction",
    currency: str = "ETB",
) -> int:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO folio_transactions (
                    folio_id, property_code, business_date, txn_type, category,
                    description, amount, currency, booking_id
                )
                VALUES (
                    :folio_id, :property_code, :business_date, :txn_type, :category,
                    :description, :amount, :currency, :booking_id
                )
                RETURNING id
                """
            ),
            {
                "folio_id": folio_id,
                "property_code": PROPERTY_CODE,
                "business_date": BUSINESS_DATE,
                "txn_type": txn_type,
                "category": category,
                "description": description,
                "amount": amount,
                "currency": currency,
                "booking_id": booking_id,
            },
        ).first()
        if txn_type == "charge":
            db.execute(
                text(
                    """
                    UPDATE folios
                    SET total_charges = COALESCE(total_charges, 0) + :amount,
                        balance = COALESCE(balance, 0) + :amount
                    WHERE id = :folio_id
                    """
                ),
                {"folio_id": folio_id, "amount": amount},
            )
        elif txn_type == "payment":
            db.execute(
                text(
                    """
                    UPDATE folios
                    SET total_payments = COALESCE(total_payments, 0) + :amount,
                        balance = COALESCE(balance, 0) - :amount
                    WHERE id = :folio_id
                    """
                ),
                {"folio_id": folio_id, "amount": amount},
            )
        db.commit()
        return int(row.id)


def _seed_notification(
    *,
    action: str = "reservation_confirmation",
    channel: str = "email",
    recipient: str | None = "guest@example.test",
    status: str = "queued",
    retry_count: int = 0,
    attempt_count: int = 0,
) -> int:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER,
                    public_request_id INTEGER,
                    guest_profile_id INTEGER,
                    guest_id VARCHAR(80),
                    property_code VARCHAR(50) NOT NULL,
                    channel VARCHAR(50) NOT NULL,
                    recipient TEXT,
                    action VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    business_date DATE,
                    status VARCHAR(50) NOT NULL DEFAULT 'queued',
                    retry_count INTEGER DEFAULT 0,
                    attempt_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMPTZ,
                    failed_at TIMESTAMPTZ,
                    failure_reason TEXT,
                    last_attempt_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        row = db.execute(
            text(
                """
                INSERT INTO guest_notification_outbox (
                    property_code, channel, recipient, action, message, business_date,
                    status, retry_count, attempt_count
                )
                VALUES (
                    :property_code, :channel, :recipient, :action, :message, :business_date,
                    :status, :retry_count, :attempt_count
                )
                RETURNING id
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "channel": channel,
                "recipient": recipient,
                "action": action,
                "message": "Permission regression notification",
                "business_date": BUSINESS_DATE,
                "status": status,
                "retry_count": retry_count,
                "attempt_count": attempt_count,
            },
        ).first()
        db.commit()
        return int(row.id)


class _SuccessfulEmailClient:
    sent: list[EmailMessagePayload]

    def __init__(self):
        self.sent = []

    def send(self, payload: EmailMessagePayload):
        self.sent.append(payload)
        return {"provider": "mock", "message_id": "mock-message"}


class _FailingEmailClient:
    def __init__(self, message: str = "mock delivery failure"):
        self.message = message

    def send(self, payload: EmailMessagePayload):
        raise RuntimeError(self.message)


def _reset_night_audit_state() -> None:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        cashier_exists = db.execute(text("SELECT to_regclass('cashier_sessions')")).scalar()
        if cashier_exists:
            db.execute(text("UPDATE cashier_sessions SET status='closed', closed_at=COALESCE(closed_at, NOW()) WHERE status <> 'closed'"))
        for table in ["night_audit_postings", "business_date_locks", "report_archive"]:
            exists = db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table}).scalar()
            if exists:
                db.execute(text(f"DELETE FROM {table}"))
        db.execute(text("UPDATE folios SET status = 'closed', total_charges = 0, total_payments = 0, balance = 0"))
        db.execute(text("UPDATE bookings SET booking_status = 'checked_out' WHERE property_code = :property_code"), {"property_code": PROPERTY_CODE})
        db.commit()


def _seed_cashier_session(
    *,
    business_date: str,
    status: str = "closed",
    variance: float = 0,
    manager_approved_by: str | None = "manager@guzo.local",
) -> int:
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cashier_sessions (
                  id SERIAL PRIMARY KEY,
                  property_code TEXT NOT NULL,
                  business_date DATE NOT NULL,
                  cashier_name TEXT NOT NULL,
                  cash NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  card NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  bank_transfer NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  mobile_money NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  unassigned NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  expected_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  declared_total NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  variance NUMERIC(12, 2) NOT NULL DEFAULT 0,
                  status TEXT NOT NULL DEFAULT 'closed',
                  notes TEXT,
                  manager_approved_by TEXT,
                  closed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        db.execute(text("ALTER TABLE cashier_sessions ADD COLUMN IF NOT EXISTS manager_approved_by TEXT"))
        row = db.execute(
            text(
                """
                INSERT INTO cashier_sessions (
                    property_code, business_date, cashier_name, expected_total,
                    declared_total, variance, status, manager_approved_by
                )
                VALUES (
                    :property_code, :business_date, 'QA Cashier', 100,
                    :declared_total, :variance, :status, :manager_approved_by
                )
                RETURNING id
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "business_date": business_date,
                "declared_total": 100 + variance,
                "variance": variance,
                "status": status,
                "manager_approved_by": manager_approved_by,
            },
        ).first()
        db.commit()
        return int(row.id)


def _open_controlled_cashier_shift(client, email: str = FINANCE_EMAIL, property_code: str = PROPERTY_CODE, business_date: str = BUSINESS_DATE, opening_float: float = 0, cashier_name: str | None = None):
    response = client.post(
        "/finance/cashier/shifts/open",
        json={"property_code": property_code, "business_date": business_date, "cashier_name": cashier_name or email, "opening_float": opening_float},
        headers=_headers(email),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_finance_user_cannot_convert_public_booking_request_and_audit_is_saved(client):
    request_id = _seed_public_booking_request()
    payload = {"total_amount_etb": 100, "room_type": "Standard Room"}

    before = _count_blocked_public_request_conversion(FINANCE_EMAIL)
    response = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json=payload,
        headers=_headers(FINANCE_EMAIL),
    )
    _assert_public_request_conversion_denied(response, FINANCE_EMAIL)
    assert _count_blocked_public_request_conversion(FINANCE_EMAIL) == before + 1


@pytest.mark.parametrize(
    "email",
    [
        RESERVATION_MANAGER_EMAIL,
        FRONT_DESK_AGENT_EMAIL,
        ADMIN_EMAIL,
    ],
)
def test_authorized_booking_hub_roles_can_convert_public_booking_request(client, email):
    request_id = _seed_public_booking_request()
    response = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"total_amount_etb": 100, "room_type": "Standard Room"},
        headers=_headers(email),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["booking_id"]
    assert body["confirmation_id"]
    assert (
        _db_scalar(
            """
            SELECT booking_status
            FROM public_booking_requests
            WHERE id = :request_id
            """,
            {"request_id": request_id},
        )
        == "converted"
    )


def test_reservations_create_valid_reservation(client):
    _reset_night_audit_state()
    payload = {
        "property_code": PROPERTY_CODE,
        "guest_name": "Reservation QA Guest",
        "guest_email": "reservation-qa@example.test",
        "guest_phone": "+251900000001",
        "check_in_date": "2026-07-01",
        "check_out_date": "2026-07-03",
        "room_type": "Standard Room",
        "rooms": 1,
        "adults": 2,
        "children": 0,
        "rate_code": "BAR",
        "reservation_type": "individual",
        "source": "direct",
        "guarantee_type": "deposit_required",
        "special_requests": "High floor",
        "vip_notes": "VIP amenity",
    }
    response = client.post("/reservations", json=payload, headers=_headers(RESERVATIONS_EMAIL))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["availability"]["is_available"] is True
    assert body["quote"]["total_etb"] > 0
    assert body["confirmation_status"] == "confirmation_queued"
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE booking_id = :booking_id
              AND action = 'reservation_confirmation'
            """,
            {"booking_id": body["booking_id"]},
        )
        == 1
    )


def test_reservations_create_repairs_missing_guest_count_columns(client):
    _reset_night_audit_state()
    _execute_schema("ALTER TABLE bookings DROP COLUMN IF EXISTS adults CASCADE")
    _execute_schema("ALTER TABLE bookings DROP COLUMN IF EXISTS children CASCADE")
    _execute_schema("ALTER TABLE bookings DROP COLUMN IF EXISTS nights CASCADE")
    try:
        response = client.post(
            "/reservations",
            json={
                "property_code": PROPERTY_CODE,
                "guest_name": "Reservation Schema Repair QA",
                "guest_email": "reservation-schema-repair@example.test",
                "check_in_date": "2026-07-21",
                "check_out_date": "2026-07-22",
                "room_type": "Standard Room",
                "rooms": 1,
                "adults": 1,
                "children": 0,
                "rate_code": "BAR",
                "reservation_type": "individual",
                "source": "direct",
                "guarantee_type": "deposit_required",
            },
            headers=_headers(RESERVATIONS_EMAIL),
        )
        assert response.status_code == 200, response.text
        booking_id = response.json()["booking_id"]
        assert (
            _db_scalar(
                """
                SELECT adults
                FROM bookings
                WHERE id = :booking_id
                """,
                {"booking_id": booking_id},
            )
            == 1
        )
    finally:
        _execute_schema("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS nights INTEGER")
        _execute_schema("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS adults INTEGER DEFAULT 1")
        _execute_schema("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS children INTEGER DEFAULT 0")


def test_reservations_block_overbooking(client):
    _reset_night_audit_state()
    payload = {
        "property_code": PROPERTY_CODE,
        "guest_name": "Overbooking QA Guest",
        "check_in_date": "2026-07-04",
        "check_out_date": "2026-07-06",
        "room_type": "Standard Room",
        "rooms": 99,
        "adults": 2,
        "children": 0,
        "rate_code": "BAR",
        "reservation_type": "group",
        "source": "group",
        "guarantee_type": "deposit_required",
    }
    response = client.post("/reservations", json=payload, headers=_headers(RESERVATIONS_EMAIL))
    assert response.status_code == 409
    assert response.json()["detail"]["message"] == "Reservation would overbook the selected room type."


def test_reservations_warn_duplicate_booking(client):
    _reset_night_audit_state()
    payload = {
        "property_code": PROPERTY_CODE,
        "guest_name": "Duplicate QA Guest",
        "guest_email": "duplicate@example.test",
        "guest_phone": "+251900000002",
        "check_in_date": "2026-07-07",
        "check_out_date": "2026-07-09",
        "room_type": "Standard Room",
        "rooms": 1,
        "adults": 1,
        "children": 0,
        "rate_code": "BAR",
        "reservation_type": "individual",
        "source": "direct",
        "guarantee_type": "deposit_required",
    }
    first = client.post("/reservations", json=payload, headers=_headers(RESERVATIONS_EMAIL))
    assert first.status_code == 200, first.text
    second = client.post("/reservations", json=payload, headers=_headers(RESERVATIONS_EMAIL))
    assert second.status_code == 200, second.text
    assert second.json()["duplicate_warnings"]


def test_public_request_conversion_blocks_when_unavailable(client):
    _reset_night_audit_state()
    today = date.fromisoformat(BUSINESS_DATE)
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        row = db.execute(
            text(
                """
                INSERT INTO public_booking_requests (
                    property_code, source, channel, guest_name, guest_email,
                    check_in_date, check_out_date, adults, children, room_type,
                    reservation_type, booking_status, guarantee_type, deposit_status, notes
                )
                VALUES (
                    :property_code, 'pytest', 'pytest', 'Unavailable QA', 'unavailable@example.test',
                    :check_in_date, :check_out_date, 1, 0, 'Suite',
                    'individual', 'pending_request', 'deposit_required', 'pending', 'unavailable regression'
                )
                RETURNING id
                """
            ),
            {
                "property_code": PROPERTY_CODE,
                "check_in_date": today,
                "check_out_date": today + timedelta(days=1),
            },
        ).first()
        db.commit()
        request_id = int(row.id)
    response = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"room_type": "Suite"},
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["availability"]["is_available"] is False


def test_public_request_cannot_reconvert_after_conversion(client):
    _reset_night_audit_state()
    request_id = _seed_public_booking_request()
    first = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"room_type": "Standard Room"},
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert first.status_code == 200, first.text
    assert first.json()["ok"] is True
    second = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"room_type": "Standard Room"},
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert second.status_code == 400
    assert "already converted" in second.json()["detail"]


def test_converted_public_request_status_cannot_be_changed(client):
    _reset_night_audit_state()
    request_id = _seed_public_booking_request()
    first = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"room_type": "Standard Room"},
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert first.status_code == 200, first.text

    response = client.patch(
        f"/booking-hub/public-requests/{request_id}/status?property_code={PROPERTY_CODE}",
        json={"status": "reviewed", "notes": "should be locked"},
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert response.status_code == 400
    assert "Converted requests cannot be changed" in response.json()["detail"]


def test_reservation_modification_unauthorized_gets_403_and_audit(client):
    _reset_night_audit_state()
    booking_id = _seed_booking(
        "confirmed",
        room_number="",
        payment_status="pending_guarantee",
        total_amount=100,
        check_in_date="2026-07-10",
        check_out_date="2026-07-11",
    )
    before = _count_denied("reservations.modify_booking", FRONTDESK_EMAIL)
    response = client.patch(
        f"/reservations/{booking_id}",
        json={"property_code": PROPERTY_CODE, "vip_notes": "Unauthorized edit attempt"},
        headers=_headers(FRONTDESK_EMAIL),
    )
    _assert_permission_denied(response, "reservations.modify_booking", FRONTDESK_EMAIL)
    assert _count_denied("reservations.modify_booking", FRONTDESK_EMAIL) == before + 1


def test_frontdesk_check_in_permission_denied_and_allowed_path(client):
    booking_id = _seed_booking("confirmed")
    permission = "frontdesk.check_in"
    payload = {"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE}

    response = client.post("/frontdesk/check-in", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, permission, FINANCE_EMAIL)

    authorized = client.post("/frontdesk/check-in", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_frontdesk_check_out_permission_denied_and_allowed_path(client):
    booking_id = _seed_booking("in_house")
    permission = "frontdesk.check_out"
    payload = {"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE}

    response = client.post("/frontdesk/check-out", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, permission, FINANCE_EMAIL)

    authorized = client.post("/frontdesk/check-out", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_walkin_booking_creation_permission_denied_and_allowed_path(client):
    permission = "frontdesk.check_in"
    payload = {
        "property_code": PROPERTY_CODE,
        "guest_name": f"Walkin Permission QA {uuid4()}",
        "check_in_date": BUSINESS_DATE,
        "check_out_date": "2026-06-03",
        "room_type": "Standard Room",
        "rate_per_night_etb": 100,
        "total_amount_etb": 100,
    }

    response = client.post("/frontdesk/walkin", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, permission, FINANCE_EMAIL)

    authorized = client.post("/frontdesk/walkin", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_housekeeping_room_status_update_permission_denied_and_allowed_path(client):
    permission = "housekeeping.mark_cleaned"
    payload = {
        "property_code": PROPERTY_CODE,
        "room_number": "QA-101",
        "business_date": BUSINESS_DATE,
        "note": "permission regression",
    }

    response = client.post("/housekeeping/mark-clean", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)

    authorized = client.post("/housekeeping/mark-clean", json=payload, headers=_headers(HOUSEKEEPING_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_housekeeping_attendant_can_mark_dirty_cleaning_clean(client):
    payload = {
        "property_code": PROPERTY_CODE,
        "room_number": "QA-101",
        "business_date": BUSINESS_DATE,
    }
    dirty = client.post("/rooms/housekeeping/mark-dirty", json=payload, headers=_headers(ATTENDANT_EMAIL))
    assert dirty.status_code == 200, dirty.text
    cleaning = client.post("/rooms/housekeeping/mark-in-service", json=payload, headers=_headers(ATTENDANT_EMAIL))
    assert cleaning.status_code == 200, cleaning.text
    clean = client.post("/rooms/housekeeping/mark-clean", json=payload, headers=_headers(ATTENDANT_EMAIL))
    assert clean.status_code == 200, clean.text
    assert (
        _db_scalar(
            """
            SELECT hk_status
            FROM housekeeping_status
            WHERE property_code = :property_code
              AND room_number = 'QA-101'
              AND business_date = :business_date
            """,
            {"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE},
        )
        == "vacant_clean"
    )


def test_housekeeping_attendant_cannot_mark_inspected(client):
    payload = {
        "property_code": PROPERTY_CODE,
        "room_number": "QA-101",
        "business_date": BUSINESS_DATE,
    }
    before = _count_denied("housekeeping.mark_inspected", ATTENDANT_EMAIL)
    response = client.post("/rooms/housekeeping/mark-inspected", json=payload, headers=_headers(ATTENDANT_EMAIL))
    _assert_permission_denied(response, "housekeeping.mark_inspected", ATTENDANT_EMAIL)
    assert _count_denied("housekeeping.mark_inspected", ATTENDANT_EMAIL) == before + 1


def test_housekeeping_supervisor_can_mark_inspected(client):
    _set_room_status("QA-101", "vacant_clean")
    payload = {
        "property_code": PROPERTY_CODE,
        "room_number": "QA-101",
        "business_date": BUSINESS_DATE,
    }
    response = client.post("/rooms/housekeeping/mark-inspected", json=payload, headers=_headers(HOUSEKEEPING_EMAIL))
    assert response.status_code == 200, response.text
    assert response.json()["hk_status"] == "vacant_inspected"


def test_finance_payment_posting_permission_denied_and_allowed_path(client):
    booking_id = _seed_booking("in_house")
    permission = "finance.post_payment"
    payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "amount": 25,
        "payment_method": "cash",
        "reference": "permission regression",
    }

    response = client.post("/finance/folio/post-payment", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)

    authorized = client.post("/finance/folio/post-payment", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_finance_charge_posting_permission_denied_and_allowed_path(client):
    booking_id = _seed_booking("in_house")
    permission = "finance.post_charge"
    payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "amount": 25,
        "category": "misc",
        "description": "permission regression",
    }

    response = client.post("/finance/folio/post-charge", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)

    authorized = client.post("/finance/folio/post-charge", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_finance_cashier_can_post_payment_and_audit_success(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    booking_id = _seed_booking("in_house")
    payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "amount": 50,
        "method": "cash",
        "description": "cashier permission regression",
    }

    response = client.post("/finance/folio/post-payment", json=payload, headers=_headers(FINANCE_EMAIL))
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'finance'
              AND action = 'folio_payment_posted'
              AND record_id = :booking_id
            """,
            {"booking_id": str(booking_id)},
        )
        >= 1
    )


def test_finance_receipt_includes_vat_service_breakdown_and_matching_totals(client):
    booking_id = _seed_booking("in_house")
    folio_id = _seed_folio(booking_id, balance=0)
    _seed_folio_transaction(folio_id, booking_id, "charge", 100, category="room", description="Room charge")
    _seed_folio_transaction(folio_id, booking_id, "charge", 30, category="fnb", description="Restaurant charge")
    _seed_folio_transaction(folio_id, booking_id, "charge", 10, category="service_charge", description="Service charge")
    _seed_folio_transaction(folio_id, booking_id, "charge", 21, category="vat", description="VAT")
    _seed_folio_transaction(folio_id, booking_id, "payment", 50, category="cash", description="Cash payment")

    response = client.get(
        f"/finance/folio/receipt?property_code={PROPERTY_CODE}&booking_id={booking_id}",
        headers=_headers(FINANCE_EMAIL),
    )
    assert response.status_code == 200, response.text
    receipt = response.json()

    assert receipt["room_charge_subtotal"] == 100
    assert receipt["fnb_other_charge_subtotal"] == 30
    assert receipt["service_charge_amount"] == 10
    assert receipt["vat_tax_amount"] == 21
    assert receipt["service_charge_percent"] == 0.1
    assert receipt["tax_percent"] == 0.15
    assert receipt["tax_service_posted"] is True
    assert receipt["total_charges"] == 161
    assert receipt["total_payments"] == 50
    assert receipt["balance"] == 111
    assert any(item["category"] == "vat" for item in receipt["line_items"])
    assert any(item["category"] == "service_charge" for item in receipt["line_items"])


def test_finance_foreign_currency_receipt_includes_original_and_base_equivalent(client):
    booking_id = _seed_booking("in_house")
    _seed_folio(booking_id, balance=0, currency="USD")

    payment = client.post(
        "/finance/folio/post-payment",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "amount": 100,
            "method": "card",
            "description": "USD payment regression",
            "currency": "USD",
            "exchange_rate_to_base": 56.5,
            "exchange_rate_source": "qa_manual",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert payment.status_code == 200, payment.text

    response = client.get(
        f"/finance/folio/receipt?property_code={PROPERTY_CODE}&booking_id={booking_id}",
        headers=_headers(FINANCE_EMAIL),
    )
    assert response.status_code == 200, response.text
    receipt = response.json()
    foreign_payment = receipt["payments"][0]

    assert foreign_payment["original_currency"] == "USD"
    assert foreign_payment["original_amount"] == 100
    assert foreign_payment["exchange_rate_to_base"] == 56.5
    assert foreign_payment["base_currency"] == "ETB"
    assert foreign_payment["base_amount"] == 5650


def test_finance_zero_tax_receipt_displays_zero_and_warning(client):
    booking_id = _seed_booking("in_house")
    folio_id = _seed_folio(booking_id, balance=0)
    _seed_folio_transaction(folio_id, booking_id, "charge", 100, category="room", description="Room charge")

    response = client.get(
        f"/finance/folio/receipt?property_code={PROPERTY_CODE}&booking_id={booking_id}",
        headers=_headers(FINANCE_EMAIL),
    )
    assert response.status_code == 200, response.text
    receipt = response.json()

    assert receipt["vat_tax_amount"] == 0
    assert receipt["service_charge_amount"] == 0
    assert receipt["tax_service_posted"] is False
    assert receipt["tax_service_warning"] == "Tax/service not posted."


def test_finance_post_quote_charges_creates_room_tax_service_transactions(client):
    booking_id = _seed_booking("confirmed", total_amount=13000)
    _seed_folio(booking_id, balance=0)

    response = client.post(
        "/finance/folio/post-quote-charges",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "room_charge_amount": 13000,
            "currency": "ETB",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["room_charge"] == 13000
    assert body["service_charge"] == 1300
    assert body["tax"] == 2145

    categories = _db_scalar(
        """
        SELECT string_agg(category, ',' ORDER BY category)
        FROM folio_transactions
        WHERE booking_id = :booking_id
        """,
        {"booking_id": booking_id},
    )
    assert categories == "room,service_charge,tax"
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'finance'
              AND action IN ('room_charge_posted_from_quote', 'tax_service_posted_from_quote')
              AND record_id = :booking_id
            """,
            {"booking_id": str(booking_id)},
        )
        == 2
    )


def test_finance_post_quote_charges_unauthorized_user_gets_403_and_audit(client):
    booking_id = _seed_booking("confirmed", total_amount=13000)
    _seed_folio(booking_id, balance=0)

    before = _count_denied("finance.post_charge", HOUSEKEEPING_EMAIL)
    response = client.post(
        "/finance/folio/post-quote-charges",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "room_charge_amount": 13000,
        },
        headers=_headers(HOUSEKEEPING_EMAIL),
    )
    _assert_permission_denied(response, "finance.post_charge", HOUSEKEEPING_EMAIL)
    assert _count_denied("finance.post_charge", HOUSEKEEPING_EMAIL) == before + 1


def test_finance_receipt_refresh_after_post_quote_charges_shows_posted_values(client):
    booking_id = _seed_booking("confirmed", total_amount=13000)
    _seed_folio(booking_id, balance=0)

    before = client.get(
        f"/finance/folio/receipt?property_code={PROPERTY_CODE}&booking_id={booking_id}",
        headers=_headers(FINANCE_EMAIL),
    )
    assert before.status_code == 200, before.text
    assert before.json()["tax_service_posted"] is False

    posted = client.post(
        "/finance/folio/post-quote-charges",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "room_charge_amount": 13000,
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert posted.status_code == 200, posted.text

    after = client.get(
        f"/finance/folio/receipt?property_code={PROPERTY_CODE}&booking_id={booking_id}",
        headers=_headers(FINANCE_EMAIL),
    )
    assert after.status_code == 200, after.text
    receipt = after.json()
    assert receipt["room_charge_subtotal"] == 13000
    assert receipt["service_charge_amount"] == 1300
    assert receipt["vat_tax_amount"] == 2145
    assert receipt["tax_service_posted"] is True
    assert len(receipt["line_items"]) == 3


def test_finance_refund_and_void_require_manager_permission(client):
    _open_controlled_cashier_shift(client, ADMIN_EMAIL)
    booking_id = _seed_booking("in_house")
    folio_id = _seed_folio(booking_id, balance=0)
    transaction_id = _seed_folio_transaction(folio_id, booking_id, "charge", 75)

    void_payload = {
        "property_code": PROPERTY_CODE,
        "transaction_id": transaction_id,
        "business_date": BUSINESS_DATE,
        "reason": "manager-only void regression",
    }
    response = client.post("/finance/folio/void-transaction", json=void_payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, "finance.void_transaction", FINANCE_EMAIL)

    authorized_void = client.post("/finance/folio/void-transaction", json=void_payload, headers=_headers(ADMIN_EMAIL))
    assert authorized_void.status_code == 200, authorized_void.text
    assert authorized_void.json()["ok"] is True

    refund_payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "amount": 10,
        "method": "cash",
        "reason": "manager-only refund regression",
    }
    response = client.post("/finance/folio/refund", json=refund_payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, "finance.void_transaction", FINANCE_EMAIL)

    authorized_refund = client.post("/finance/folio/refund", json=refund_payload, headers=_headers(ADMIN_EMAIL))
    assert authorized_refund.status_code == 200, authorized_refund.text
    assert authorized_refund.json()["ok"] is True


def test_finance_cashier_close_records_expected_vs_actual_totals(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL, cashier_name="QA Cashier")
    booking_id = _seed_booking("in_house")
    payment_payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "amount": 40,
        "method": "cash",
        "description": "cashier close regression",
    }
    payment = client.post("/finance/folio/post-payment", json=payment_payload, headers=_headers(FINANCE_EMAIL))
    assert payment.status_code == 200, payment.text

    close_payload = {
        "property_code": PROPERTY_CODE,
        "business_date": BUSINESS_DATE,
        "cashier_name": "QA Cashier",
        "actual_cash": 40,
        "actual_card": 0,
        "actual_bank_transfer": 0,
        "actual_mobile_money": 0,
        "notes": "permission regression close",
    }
    response = client.post("/finance/cashier/close", json=close_payload, headers=_headers(FINANCE_EMAIL))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["expected_total"] >= 40
    assert body["declared_total"] >= 40
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM cashier_sessions
            WHERE cashier_name = 'QA Cashier'
              AND business_date = :business_date
            """,
            {"business_date": BUSINESS_DATE},
        )
        == 1
    )


def test_night_audit_run_permission_denied_and_allowed_path(client):
    permission = "night_audit.run_audit"
    payload = {"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "notes": "permission regression"}

    response = client.post("/night-audit/run", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, permission, FINANCE_EMAIL)

    authorized = client.post("/night-audit/run", json=payload, headers=_headers(NIGHT_AUDIT_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_night_audit_override_permission_denied_and_allowed_path(client):
    permission = "night_audit.override_exception"
    payload = {
        "property_code": PROPERTY_CODE,
        "business_date": BUSINESS_DATE,
        "exception_key": "permission_regression",
        "reason": "permission regression",
    }

    response = client.post("/night-audit/override-exception", json=payload, headers=_headers(FINANCE_EMAIL))
    _assert_permission_denied(response, permission, FINANCE_EMAIL)

    authorized = client.post("/night-audit/override-exception", json=payload, headers=_headers(ADMIN_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_admin_user_create_permission_denied_and_allowed_path(client):
    permission = "admin.manage_users"
    payload = {
        "full_name": "Permission QA Create",
        "email": f"permission-create-{uuid4()}@example.test",
        "role_key": "read_only_owner",
        "property_code": PROPERTY_CODE,
        "is_active": True,
    }

    response = client.post("/admin/users", json=payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)

    authorized = client.post("/admin/users", json=payload, headers=_headers(ADMIN_EMAIL))
    _assert_authorized_reaches_normal_path(authorized, permission)


def test_admin_user_update_disable_reset_permission_denied_and_allowed_paths(client):
    user_id = _seed_admin_user()
    permission = "admin.manage_users"

    update_payload = {"full_name": "Permission QA Updated"}
    response = client.patch(f"/admin/users/{user_id}", json=update_payload, headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)
    authorized_update = client.patch(f"/admin/users/{user_id}", json=update_payload, headers=_headers(ADMIN_EMAIL))
    _assert_authorized_reaches_normal_path(authorized_update, permission)

    response = client.post(f"/admin/users/{user_id}/disable", headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)
    authorized_disable = client.post(f"/admin/users/{user_id}/disable", headers=_headers(ADMIN_EMAIL))
    _assert_authorized_reaches_normal_path(authorized_disable, permission)

    response = client.post(f"/admin/users/{user_id}/reset-password", headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, permission, FRONTDESK_EMAIL)
    authorized_reset = client.post(f"/admin/users/{user_id}/reset-password", headers=_headers(ADMIN_EMAIL))
    _assert_authorized_reaches_normal_path(authorized_reset, permission)


def test_frontdesk_lifecycle_successful_check_in(client):
    _set_room_status("QA-101", "vacant_inspected")
    booking_id = _seed_booking("confirmed", room_number="QA-101", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    assert response.json()["booking_status"] == "in_house"


def test_frontdesk_lifecycle_blocks_check_in_without_room(client):
    booking_id = _seed_booking("confirmed", room_number="", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 409
    assert "Room assignment required" in response.json()["detail"]


def test_frontdesk_lifecycle_blocks_check_in_if_room_dirty(client):
    _set_room_status("QA-102", "vacant_dirty")
    booking_id = _seed_booking("confirmed", room_number="QA-102", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 409
    assert "not ready" in response.json()["detail"]


def test_frontdesk_lifecycle_blocks_check_in_if_room_clean_but_uninspected(client):
    _set_room_status("QA-101", "vacant_clean")
    booking_id = _seed_booking("confirmed", room_number="QA-101", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 409
    assert "inspected" in response.json()["detail"]


def test_frontdesk_q_reservation_persists_without_checking_in(client):
    booking_id = _seed_booking("confirmed", room_number="QA-101", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/q/place",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "q_priority": "vip",
            "q_notes": "Guest arrived early; room pending inspection.",
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["q_status"] == "waiting"
    assert body["q_priority"] == "vip"
    assert body["booking_status"] == "confirmed"
    assert _count_audit_action("reservation_placed_on_q", booking_id) >= 1

    removed = client.post(
        "/frontdesk/q/remove",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["q_status"] == "removed"
    assert _count_audit_action("reservation_removed_from_q", booking_id) >= 1


def test_frontdesk_manual_authorization_registration_and_upsell_persist(client):
    booking_id = _seed_booking("confirmed", room_number="QA-101", payment_status="pending")

    unauthorized = client.post(
        "/frontdesk/manual-authorization",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "authorization_amount": 500,
            "authorization_type": "offline",
            "authorization_code": "QA-AUTH",
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    _assert_permission_denied(unauthorized, "reservations.mark_guaranteed", FRONTDESK_EMAIL)

    authorization = client.post(
        "/frontdesk/manual-authorization",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "authorization_amount": 500,
            "authorization_type": "offline",
            "authorization_code": "QA-AUTH",
            "authorization_notes": "Manual/offline authorization regression.",
        },
        headers=_headers(ADMIN_EMAIL),
    )
    assert authorization.status_code == 200, authorization.text
    assert authorization.json()["authorization_status"] == "manual_authorized"
    assert float(authorization.json()["authorization_amount"]) == 500
    assert _count_audit_action("manual_authorization_recorded", booking_id) >= 1

    generated = client.post(
        "/frontdesk/registration-card/generated",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["registration_card_generated_at"] is not None
    assert generated.json()["registration_card_signed"] is False
    assert _count_audit_action("registration_card_generated", booking_id) >= 1

    signed = client.post(
        "/frontdesk/registration-card/signed",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "signed": True,
            "notes": "Guest acknowledged registration card.",
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["registration_card_signed"] is True
    assert _count_audit_action("registration_card_signed", booking_id) >= 1

    upsell = client.post(
        "/frontdesk/upsell",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "offered": True,
            "accepted": True,
            "from_room_type": "Standard Room",
            "to_room_type": "Deluxe Room",
            "amount_per_night": 1200,
            "total_amount": 1200,
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert upsell.status_code == 200, upsell.text
    assert upsell.json()["upsell_accepted"] is True
    assert upsell.json()["room_type"] == "Standard Room"
    assert _count_audit_action("upsell_accepted", booking_id) >= 1


def test_frontdesk_check_in_from_q_uses_existing_readiness_rules_and_audits(client):
    _set_room_status("QA-101", "vacant_inspected")
    booking_id = _seed_booking("confirmed", room_number="QA-101", payment_status="deposit_paid")
    q_response = client.post(
        "/frontdesk/q/place",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert q_response.status_code == 200, q_response.text

    check_in = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert check_in.status_code == 200, check_in.text
    assert check_in.json()["booking_status"] == "in_house"
    assert _count_audit_action("check_in_completed_from_q", booking_id) >= 1


def test_frontdesk_check_in_blocked_by_readiness_writes_audit(client):
    _set_room_status("QA-102", "vacant_dirty")
    booking_id = _seed_booking("confirmed", room_number="QA-102", payment_status="deposit_paid")
    response = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 409
    assert _count_audit_action("check_in_blocked_by_readiness", booking_id) >= 1


def test_frontdesk_lifecycle_successful_checkout(client):
    _set_room_status("QA-101", "occupied_clean", is_occupied=True)
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="paid", total_amount=0)
    folio_id = _seed_folio(booking_id, balance=0)
    response = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    assert response.json()["booking_status"] == "checked_out"
    assert _db_scalar("SELECT status FROM folios WHERE id = :id", {"id": folio_id}) == "closed"
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE booking_id = :booking_id
              AND action = 'guest_feedback_request'
            """,
            {"booking_id": booking_id},
        )
        == 1
    )


def test_frontdesk_lifecycle_blocks_checkout_with_unpaid_balance(client):
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="pending", total_amount=100)
    _seed_folio(booking_id, balance=100)
    response = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 409
    assert "Folio balance must be zero" in response.json()["detail"]


def test_frontdesk_lifecycle_checkout_allowed_after_payment(client):
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    _set_room_status("QA-101", "occupied_clean", is_occupied=True)
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="pending", total_amount=100)
    folio_id = _seed_folio(booking_id, balance=0)
    _seed_folio_transaction(folio_id, booking_id, "charge", 100)

    blocked = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert blocked.status_code == 409

    payment = client.post(
        "/finance/folio/post-payment",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "amount": 100,
            "method": "cash",
            "description": "checkout settlement regression",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert payment.status_code == 200, payment.text

    checkout = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["booking_status"] == "checked_out"


def test_booking_to_night_audit_e2e_flow(client):
    _reset_night_audit_state()
    request_id = _seed_public_booking_request()
    converted = client.post(
        f"/booking-hub/public-requests/{request_id}/convert?property_code={PROPERTY_CODE}",
        json={"total_amount_etb": 100, "room_type": "Standard Room"},
        headers=_headers(ADMIN_EMAIL),
    )
    assert converted.status_code == 200, converted.text
    booking_id = converted.json()["booking_id"]

    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE bookings
                SET room_number = 'QA-101',
                    payment_status = 'deposit_paid',
                    booking_status = 'confirmed'
                WHERE id = :booking_id
                """
            ),
            {"booking_id": booking_id},
        )
        db.commit()

    _set_room_status("QA-101", "vacant_inspected")
    check_in = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert check_in.status_code == 200, check_in.text
    assert check_in.json()["booking_status"] == "in_house"

    _seed_folio(booking_id, balance=0)
    charge = client.post(
        "/finance/folio/post-charge",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "amount": 100,
            "category": "room",
            "description": "E2E room charge",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert charge.status_code == 200, charge.text

    shift = _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    payment = client.post(
        "/finance/folio/post-payment",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "amount": 100,
            "method": "cash",
            "description": "E2E settlement",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert payment.status_code == 200, payment.text

    _set_room_status("QA-101", "occupied_clean", is_occupied=True)
    checkout = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["booking_status"] == "checked_out"

    declared = client.post(
        f"/finance/cashier/shifts/{shift['id']}/declare",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "cash": 100,
            "card": 0,
            "bank_transfer": 0,
            "mobile_money": 0,
            "unassigned": 0,
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert declared.status_code == 200, declared.text
    closed = client.post(
        f"/finance/cashier/shifts/{shift['id']}/close",
        json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE},
        headers=_headers(FINANCE_EMAIL),
    )
    assert closed.status_code == 200, closed.text

    audit = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "notes": "E2E production-candidate flow"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert audit.status_code == 200, audit.text
    body = audit.json()
    assert body["ok"] is True
    assert body["next_business_date"] == "2026-06-03"


def test_frontdesk_lifecycle_unauthorized_checkout_gets_403_and_audit(client):
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="paid", total_amount=0)
    before = _count_denied("frontdesk.check_out", FINANCE_EMAIL)
    response = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FINANCE_EMAIL),
    )
    _assert_permission_denied(response, "frontdesk.check_out", FINANCE_EMAIL)
    assert _count_denied("frontdesk.check_out", FINANCE_EMAIL) == before + 1


def test_night_audit_hard_close_blocks_pending_departures(client):
    _reset_night_audit_state()
    audit_date = "2026-06-20"
    booking_id = _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="paid",
        total_amount=0,
        check_in_date="2026-06-19",
        check_out_date=audit_date,
    )
    _seed_folio(booking_id, balance=0)

    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "pending departure regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert any(item["exception_key"] == "frontdesk_departures_remaining" for item in body["blocking_exceptions"])


def test_night_audit_hard_close_blocks_unpaid_open_folio(client):
    _reset_night_audit_state()
    audit_date = "2026-06-21"
    booking_id = _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="pending",
        total_amount=100,
        check_in_date=audit_date,
        check_out_date="2026-06-23",
    )
    _seed_folio(booking_id, balance=100)

    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "unpaid folio regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert any(item["exception_key"] == "open_folios_with_balance" for item in body["blocking_exceptions"])


def test_night_audit_hard_close_blocks_unclosed_cashier_shift(client):
    _reset_night_audit_state()
    audit_date = "2026-06-22"
    _seed_cashier_session(business_date=audit_date, status="open", variance=0)

    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "open cashier regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert any(item["exception_key"] == "open_cashier_shifts" for item in body["blocking_exceptions"])


def test_night_audit_hard_close_blocks_unapproved_cashier_variance(client):
    _reset_night_audit_state()
    audit_date = "2026-06-23"
    _seed_cashier_session(
        business_date=audit_date,
        status="variance_review",
        variance=5,
        manager_approved_by=None,
    )

    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "variance regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert any(item["exception_key"] == "unapproved_cashier_variance" for item in body["blocking_exceptions"])


def test_night_audit_hard_close_succeeds_and_locks_business_date(client):
    _reset_night_audit_state()
    audit_date = "2026-06-24"
    booking_id = _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="paid",
        total_amount=0,
        check_in_date=audit_date,
        check_out_date="2026-06-26",
    )
    _seed_folio(booking_id, balance=0)
    _seed_cashier_session(business_date=audit_date, status="closed", variance=0)

    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "success regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["next_business_date"] == "2026-06-25"
    assert body["posting_summary"]["posted_transactions"] >= 3
    assert body["report_package"]["occupancy_summary"]["in_house"] >= 1
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM business_date_locks
            WHERE property_code = :property_code
              AND business_date = :business_date
              AND status = 'locked'
            """,
            {"property_code": PROPERTY_CODE, "business_date": audit_date},
        )
        == 1
    )
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'night_audit'
              AND action = 'business_date_locked'
              AND record_id = :business_date
            """,
            {"business_date": audit_date},
        )
        >= 1
    )


def test_closed_business_date_blocks_normal_finance_and_frontdesk_edits(client):
    _reset_night_audit_state()
    audit_date = "2026-06-25"
    booking_id = _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="paid",
        total_amount=0,
        check_in_date=audit_date,
        check_out_date="2026-06-27",
    )
    _seed_folio(booking_id, balance=0)
    _seed_cashier_session(business_date=audit_date, status="closed", variance=0)
    close = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": audit_date, "notes": "lock edit regression"},
        headers=_headers(NIGHT_AUDIT_EMAIL),
    )
    assert close.status_code == 200, close.text
    assert close.json()["ok"] is True

    finance = client.post(
        "/finance/folio/post-payment",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": audit_date,
            "amount": 10,
            "method": "cash",
            "description": "locked date edit regression",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert finance.status_code == 409
    assert "locked by Night Audit" in finance.json()["detail"]

    _set_room_status("QA-103", "vacant_inspected")
    new_booking_id = _seed_booking(
        "confirmed",
        room_number="QA-103",
        payment_status="deposit_paid",
        total_amount=0,
        check_in_date=audit_date,
        check_out_date="2026-06-26",
    )
    frontdesk = client.post(
        "/frontdesk/check-in",
        json={"property_code": PROPERTY_CODE, "booking_id": new_booking_id, "business_date": audit_date},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert frontdesk.status_code == 409
    assert "locked by Night Audit" in frontdesk.json()["detail"]


def test_night_audit_manager_override_is_audited(client):
    _reset_night_audit_state()
    response = client.post(
        "/night-audit/override-exception",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": "2026-06-26",
            "exception_key": "unapproved_cashier_variance",
            "override_reason": "GM approved variance for permission regression",
        },
        headers=_headers(ADMIN_EMAIL),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'night_audit'
              AND action = 'night_audit_manager_override'
              AND record_id = 'unapproved_cashier_variance'
            """
        )
        >= 1
    )


def test_night_audit_unauthorized_role_gets_403_and_audit(client):
    _reset_night_audit_state()
    before = _count_denied("night_audit.run_audit", FINANCE_EMAIL)
    response = client.post(
        "/night-audit/run",
        json={"property_code": PROPERTY_CODE, "business_date": "2026-06-27", "notes": "unauthorized regression"},
        headers=_headers(FINANCE_EMAIL),
    )
    _assert_permission_denied(response, "night_audit.run_audit", FINANCE_EMAIL)
    assert _count_denied("night_audit.run_audit", FINANCE_EMAIL) == before + 1


def test_guest_profile_created_and_linked_from_reservation_with_confirmation_queue(client):
    arrival = "2027-01-10"
    payload = {
        "property_code": PROPERTY_CODE,
        "guest_name": "Guest Profile QA",
        "guest_email": "guest-profile-qa@example.test",
        "guest_phone": "251911111111",
        "check_in_date": arrival,
        "check_out_date": "2027-01-12",
        "room_type": "Standard Room",
        "rooms": 1,
        "adults": 1,
        "children": 0,
        "rate_code": "BAR",
        "source": "direct",
        "reservation_type": "individual",
        "vip_notes": "VIP arrival regression",
    }
    response = client.post("/reservations", json=payload, headers=_headers(RESERVATIONS_EMAIL))
    assert response.status_code == 200, response.text
    body = response.json()
    booking_id = body["booking_id"]
    assert body["guest_id"].startswith(f"GST-{PROPERTY_CODE}-")
    assert body["guest_notification_status"] == "queued"
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_profiles gp
            JOIN bookings b ON b.guest_profile_id = gp.id
            WHERE b.id = :booking_id
              AND gp.email = :email
            """,
            {"booking_id": booking_id, "email": payload["guest_email"]},
        )
        == 1
    )
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE booking_id = :booking_id
              AND action = 'reservation_confirmation'
              AND status = 'queued'
              AND retry_count = 0
            """,
            {"booking_id": booking_id},
        )
        == 1
    )
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM manager_alerts
            WHERE booking_id = :booking_id
              AND alert_type = 'vip_arrival'
              AND status = 'open'
            """,
            {"booking_id": booking_id},
        )
        == 1
    )


def test_checkout_queues_feedback_request_with_guest_profile(client):
    _set_room_status("QA-101", "occupied_clean", is_occupied=True)
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="paid", total_amount=0)
    _seed_folio(booking_id, balance=0)
    response = client.post(
        "/frontdesk/check-out",
        json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox n
            JOIN guest_profiles gp ON gp.id = n.guest_profile_id
            WHERE n.booking_id = :booking_id
              AND n.action = 'guest_feedback_request'
              AND n.status = 'queued'
            """,
            {"booking_id": booking_id},
        )
        == 1
    )


def test_low_feedback_rating_queues_manager_alert(client):
    booking_id = _seed_booking("checked_out", room_number="QA-101", payment_status="paid", total_amount=0)
    response = client.post(
        "/guest-feedback",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "guest_name": "Low Rating QA",
            "rating": 2.5,
            "feedback_source": "front_desk",
            "comment": "Needs manager follow up",
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["guest_id"].startswith(f"GST-{PROPERTY_CODE}-")
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM manager_alerts
            WHERE booking_id = :booking_id
              AND alert_type = 'low_feedback_rating'
              AND severity = 'high'
              AND status = 'open'
            """,
            {"booking_id": booking_id},
        )
        == 1
    )


def test_guest_profile_edit_unauthorized_gets_403_and_audit(client):
    create = client.post(
        "/reservations",
        json={
            "property_code": PROPERTY_CODE,
            "guest_name": "Profile Edit QA",
            "guest_email": "profile-edit-qa@example.test",
            "guest_phone": "251922222222",
            "check_in_date": "2027-02-01",
            "check_out_date": "2027-02-02",
            "room_type": "Standard Room",
            "rooms": 1,
            "adults": 1,
            "children": 0,
            "rate_code": "BAR",
            "source": "direct",
            "reservation_type": "individual",
        },
        headers=_headers(RESERVATIONS_EMAIL),
    )
    assert create.status_code == 200, create.text
    guest_id = create.json()["guest_id"]

    view = client.get(f"/guest-profiles/{guest_id}?property_code={PROPERTY_CODE}", headers=_headers(FRONTDESK_EMAIL))
    assert view.status_code == 200, view.text

    before = _count_denied("guest.edit_profile", FRONTDESK_EMAIL)
    denied = client.patch(
        f"/guest-profiles/{guest_id}",
        json={"property_code": PROPERTY_CODE, "nationality": "ET", "vip_flag": True},
        headers=_headers(FRONTDESK_EMAIL),
    )
    _assert_permission_denied(denied, "guest.edit_profile", FRONTDESK_EMAIL)
    assert _count_denied("guest.edit_profile", FRONTDESK_EMAIL) == before + 1

    allowed = client.patch(
        f"/guest-profiles/{guest_id}",
        json={"property_code": PROPERTY_CODE, "nationality": "ET", "vip_flag": True},
        headers=_headers(ADMIN_EMAIL),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["nationality"] == "ET"
    assert allowed.json()["vip_flag"] is True


def test_notification_worker_sends_queued_confirmation_with_mocked_email_client(client):
    notification_id = _seed_notification(action="reservation_confirmation", recipient="confirm@example.test")
    email_client = _SuccessfulEmailClient()
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        result = process_email_outbox(
            db,
            property_code=PROPERTY_CODE,
            actor_email=ADMIN_EMAIL,
            email_client=email_client,
        )
        db.commit()
    assert result["sent_count"] >= 1
    assert any(message.to_email == "confirm@example.test" for message in email_client.sent)
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE id = :id
              AND status = 'sent'
              AND sent_at IS NOT NULL
              AND attempt_count = 1
            """,
            {"id": notification_id},
        )
        == 1
    )


def test_notification_worker_skips_no_recipient_notification(client):
    notification_id = _seed_notification(action="pre_arrival_reminder", recipient=None)
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        result = process_email_outbox(
            db,
            property_code=PROPERTY_CODE,
            actor_email=ADMIN_EMAIL,
            email_client=_SuccessfulEmailClient(),
        )
        db.commit()
    assert result["skipped_count"] == 1
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE id = :id
              AND status = 'skipped'
              AND failure_reason = 'no_recipient'
            """,
            {"id": notification_id},
        )
        == 1
    )


def test_notification_worker_marks_failed_and_increments_retry_count(client):
    notification_id = _seed_notification(action="checkout_receipt", recipient="fail@example.test")
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        result = process_email_outbox(
            db,
            property_code=PROPERTY_CODE,
            actor_email=ADMIN_EMAIL,
            email_client=_FailingEmailClient("smtp refused"),
        )
        db.commit()
    assert result["failed_count"] >= 1
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE id = :id
              AND status = 'failed'
              AND retry_count = 1
              AND attempt_count = 1
              AND failed_at IS NOT NULL
              AND last_attempt_at IS NOT NULL
              AND failure_reason = 'smtp refused'
            """,
            {"id": notification_id},
        )
        == 1
    )


def test_notification_worker_creates_manager_alert_after_repeated_failure(client, monkeypatch):
    monkeypatch.setenv("GUZO_EMAIL_MAX_RETRIES", "3")
    notification_id = _seed_notification(
        action="feedback_request",
        recipient="repeat-fail@example.test",
        retry_count=2,
        attempt_count=2,
    )
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        result = process_email_outbox(
            db,
            property_code=PROPERTY_CODE,
            actor_email=ADMIN_EMAIL,
            email_client=_FailingEmailClient("provider timeout"),
        )
        db.commit()
    assert result["failed_count"] >= 1
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM manager_alerts
            WHERE alert_type = 'failed_guest_message'
              AND severity = 'high'
              AND status = 'open'
              AND message LIKE :message
            """,
            {"message": f"%{notification_id}%provider timeout%"},
        )
        == 1
    )


def test_notification_queue_access_unauthorized_gets_403_and_audit(client):
    _seed_notification(action="booking_cancellation", recipient="blocked@example.test")
    before = _count_denied("notifications.view_queue", FRONTDESK_EMAIL)
    response = client.get(f"/notifications/outbox?property_code={PROPERTY_CODE}", headers=_headers(FRONTDESK_EMAIL))
    _assert_permission_denied(response, "notifications.view_queue", FRONTDESK_EMAIL)
    assert _count_denied("notifications.view_queue", FRONTDESK_EMAIL) == before + 1

    authorized = client.get(f"/notifications/outbox?property_code={PROPERTY_CODE}", headers=_headers(ADMIN_EMAIL))
    assert authorized.status_code == 200, authorized.text


def test_auth_login_success_and_current_user(client):
    _seed_auth_user(email="auth-admin@example.test", password="Password123!", role_key="admin")
    login = client.post(
        "/auth/login",
        json={"email": "auth-admin@example.test", "password": "Password123!", "property_code": PROPERTY_CODE},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "auth-admin@example.test"


def test_auth_invalid_login_rejected(client):
    _seed_auth_user(email="auth-invalid@example.test", password="Password123!", role_key="frontdesk_agent")
    response = client.post(
        "/auth/login",
        json={"email": "auth-invalid@example.test", "password": "wrong", "property_code": PROPERTY_CODE},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_auth_disabled_user_rejected(client):
    _seed_auth_user(
        email="auth-disabled@example.test",
        password="Password123!",
        role_key="frontdesk_agent",
        is_active=False,
    )
    response = client.post(
        "/auth/login",
        json={"email": "auth-disabled@example.test", "password": "Password123!", "property_code": PROPERTY_CODE},
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_jwt_authenticated_user_can_access_allowed_endpoint(client):
    _seed_auth_user(email="auth-frontdesk@example.test", password="Password123!", role_key="frontdesk_agent")
    token = _login_token(client, "auth-frontdesk@example.test")
    _seed_booking("confirmed", room_number="", payment_status="pending", check_in_date=BUSINESS_DATE)
    response = client.get(
        f"/frontdesk/bookings?scope=today&date={BUSINESS_DATE}&property={PROPERTY_CODE}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


def test_jwt_unauthorized_role_gets_403_and_audit(client):
    email = "auth-finance@example.test"
    _seed_auth_user(email=email, password="Password123!", role_key="finance_cashier")
    token = _login_token(client, email)
    before = _count_denied("booking.review_public_request", email)
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "create_reservation_request",
            "property_code": PROPERTY_CODE,
            "data": {
                "guest_name": "JWT Blocked Guest",
                "check_in_date": "2027-04-01",
                "check_out_date": "2027-04-02",
                "room_type": "Standard Room",
                "source": "agent_harness",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert_permission_denied(response, "booking.review_public_request", email)
    assert _count_denied("booking.review_public_request", email) == before + 1


def test_missing_token_gets_401_when_dev_fallback_disabled(client, monkeypatch):
    monkeypatch.setenv("GUZO_AUTH_DEV_FALLBACK", "false")
    response = client.get(f"/notifications/outbox?property_code={PROPERTY_CODE}")
    assert response.status_code == 401
    assert "Authentication token is required" in response.json()["detail"]


def test_development_header_fallback_still_works_when_enabled(client, monkeypatch):
    monkeypatch.setenv("GUZO_AUTH_DEV_FALLBACK", "true")
    response = client.get(f"/notifications/outbox?property_code={PROPERTY_CODE}", headers=_headers(ADMIN_EMAIL))
    assert response.status_code == 200, response.text


def test_agent_harness_creates_pending_reservation_request(client):
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "create_reservation_request",
            "property_code": PROPERTY_CODE,
            "data": {
                "guest_name": "Agent Harness Guest",
                "guest_email": "agent-harness@example.test",
                "check_in_date": "2027-03-01",
                "check_out_date": "2027-03-03",
                "room_type": "Standard Room",
                "source": "agent_harness",
            },
        },
        headers=_headers(RESERVATIONS_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "created"
    assert body["task_name"] == "create_reservation_request"
    request_id = body["data"]["public_request_id"]
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM public_booking_requests
            WHERE id = :request_id
              AND booking_status = 'pending_request'
              AND source = 'agent_harness'
            """,
            {"request_id": request_id},
        )
        == 1
    )


def test_agent_harness_suggests_clean_room_without_assignment(client):
    booking_id = _seed_booking("confirmed", room_number="", payment_status="deposit_paid", check_in_date="2027-03-10")
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "suggest_room_assignment",
            "property_code": PROPERTY_CODE,
            "data": {
                "booking_id": booking_id,
                "room_type": "Standard Room",
                "check_in_date": "2027-03-10",
            },
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "suggested"
    assert body["data"]["booking_id"] == booking_id
    assert body["data"]["suggested_rooms"]
    assert _db_scalar("SELECT COALESCE(room_number, '') FROM bookings WHERE id = :id", {"id": booking_id}) == ""


def test_agent_harness_creates_housekeeping_task(client):
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "create_housekeeping_task",
            "property_code": PROPERTY_CODE,
            "data": {
                "room_number": "QA-102",
                "task_type": "cleaning",
                "priority": "high",
                "business_date": BUSINESS_DATE,
                "assigned_to": "QA Attendant",
            },
        },
        headers=_headers(HOUSEKEEPING_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "created"
    assert body["data"]["hk_status"] == "service_in_progress"
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM housekeeping_status
            WHERE property_code = :property_code
              AND room_number = 'QA-102'
              AND business_date = :business_date
              AND hk_status = 'service_in_progress'
              AND assigned_to = 'QA Attendant'
            """,
            {"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE},
        )
        == 1
    )


def test_agent_harness_explains_check_in_blocked(client):
    booking_id = _seed_booking("confirmed", room_number="", payment_status="pending", check_in_date=BUSINESS_DATE)
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "explain_check_in_blocked",
            "property_code": PROPERTY_CODE,
            "data": {"booking_id": booking_id, "business_date": BUSINESS_DATE},
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    blocker_codes = {blocker["code"] for blocker in body["data"]["blockers"]}
    assert "room_assignment_required" in blocker_codes
    assert "guarantee_required" in blocker_codes
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'agent_harness'
              AND action = 'agent_explain_check_in_blocked'
              AND record_id = :booking_id
            """,
            {"booking_id": str(booking_id)},
        )
        >= 1
    )


def test_agent_harness_summarizes_front_desk_issues(client):
    _seed_booking("confirmed", room_number="", payment_status="pending", check_in_date=BUSINESS_DATE)
    _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="paid",
        check_in_date="2026-06-01",
        check_out_date=BUSINESS_DATE,
    )
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "summarize_front_desk_issues",
            "property_code": PROPERTY_CODE,
            "data": {"business_date": BUSINESS_DATE},
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "summary"
    assert body["data"]["pending_arrivals"] >= 1
    assert body["data"]["pending_departures"] >= 1
    assert body["data"]["missing_room_assignments"] >= 1
    assert body["data"]["missing_guarantees"] >= 1


def test_agent_harness_summarizes_pending_manager_alerts(client):
    _execute_schema(
        """
        CREATE TABLE IF NOT EXISTS manager_alerts (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            booking_id INTEGER,
            alert_type VARCHAR(80),
            severity VARCHAR(30),
            message TEXT,
            status VARCHAR(30) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _execute_schema(
        """
        INSERT INTO manager_alerts (property_code, alert_type, severity, message, status)
        VALUES ('DRE001', 'vip_arrival', 'high', 'VIP arrival needs manager attention', 'open')
        """
    )
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "summarize_manager_alerts",
            "property_code": PROPERTY_CODE,
            "data": {"status": "open"},
        },
        headers=_headers(ADMIN_EMAIL),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "summary"
    assert body["data"]["open_alert_count"] >= 1
    assert body["data"]["by_severity"]["high"] >= 1


def test_agent_harness_check_in_explanation_tolerates_housekeeping_status_without_id(client):
    _execute_schema("ALTER TABLE housekeeping_status DROP COLUMN IF EXISTS id CASCADE")
    try:
        _set_room_status("QA-103", "vacant_inspected", is_occupied=False)
        booking_id = _seed_booking(
            "confirmed",
            room_number="QA-103",
            payment_status="deposit_paid",
            check_in_date=BUSINESS_DATE,
        )
        response = client.post(
            "/agent-harness/tasks",
            json={
                "task_name": "explain_check_in_blocked",
                "property_code": PROPERTY_CODE,
                "data": {"booking_id": booking_id, "business_date": BUSINESS_DATE},
            },
            headers=_headers(FRONTDESK_EMAIL),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["task_name"] == "explain_check_in_blocked"
        assert body["data"]["room_readiness"]["room_status"] == "vacant_inspected"
    finally:
        _execute_schema("ALTER TABLE housekeeping_status ADD COLUMN IF NOT EXISTS id BIGSERIAL")


def test_frontdesk_bookings_tolerates_housekeeping_status_without_id(client):
    _execute_schema("ALTER TABLE housekeeping_status DROP COLUMN IF EXISTS id CASCADE")
    try:
        _set_room_status("QA-103", "vacant_inspected", is_occupied=False)
        booking_id = _seed_booking(
            "confirmed",
            room_number="QA-103",
            payment_status="deposit_paid",
            check_in_date=BUSINESS_DATE,
        )
        response = client.get(
            f"/frontdesk/bookings?scope=today&date={BUSINESS_DATE}&property={PROPERTY_CODE}",
            headers=_headers(FRONTDESK_EMAIL),
        )
        assert response.status_code == 200, response.text
        rows = response.json()
        row = next((item for item in rows if item["id"] == booking_id), None)
        assert row is not None
        assert row["housekeeping_status"] == "vacant_inspected"
    finally:
        _execute_schema("ALTER TABLE housekeeping_status ADD COLUMN IF NOT EXISTS id BIGSERIAL")


def test_frontdesk_service_records_persist_filter_and_audit(client):
    booking_id = _seed_booking(
        "in_house",
        room_number="QA-101",
        payment_status="paid",
        check_in_date=BUSINESS_DATE,
    )
    create_response = client.post(
        "/frontdesk/service-records",
        json={
            "record_type": "guest_message",
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "reservation_reference": f"QA-{booking_id}",
            "guest_name": "Service Record Guest",
            "room_number": "QA-101",
            "status": "open",
            "priority": "high",
            "assigned_to": "Front Desk",
            "notes": "Guest requested extra towels.",
            "task_key": f"message-{booking_id}",
            "title": "Guest message",
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["property_code"] == PROPERTY_CODE
    assert created["status_label"] == "Open"
    assert created["booking_id"] == booking_id

    listed = client.get(
        f"/frontdesk/service-records?property_code={PROPERTY_CODE}&record_type=guest_message",
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == created["id"] for row in listed.json())

    other_property = client.get(
        "/frontdesk/service-records?property_code=NN002&record_type=guest_message",
        headers=_headers(ADMIN_EMAIL),
    )
    assert other_property.status_code == 200, other_property.text
    assert all(row["property_code"] == "NN002" for row in other_property.json())
    assert not any(row["id"] == created["id"] for row in other_property.json())

    completed = client.patch(
        f"/frontdesk/service-records/{created['id']}?property_code={PROPERTY_CODE}",
        json={"status": "completed", "notes": "Delivered to housekeeping."},
        headers=_headers(FRONTDESK_EMAIL),
    )
    assert completed.status_code == 200, completed.text
    completed_body = completed.json()
    assert completed_body["status"] == "completed"
    assert completed_body["status_label"] == "Completed"
    assert completed_body["completed_at"]
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'frontdesk'
              AND action IN (
                'frontdesk_service_record_created',
                'frontdesk_service_record_status_updated'
              )
              AND record_id = :record_id
            """,
            {"record_id": str(created["id"])},
        )
        == 2
    )


def test_notification_outbox_endpoints_use_stable_sql_aliases(client, monkeypatch):
    monkeypatch.setenv("GUZO_EMAIL_PROVIDER", "disabled")
    notification_id = _seed_notification(action="reservation_confirmation", recipient="alias-regression@example.test")

    listed = client.get(
        f"/notifications/outbox?property_code={PROPERTY_CODE}&status_filter=queued",
        headers=_headers(ADMIN_EMAIL),
    )
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == notification_id for row in listed.json())

    processed = client.post(
        f"/notifications/process-outbox?property_code={PROPERTY_CODE}&limit=5",
        headers=_headers(ADMIN_EMAIL),
    )
    assert processed.status_code == 200, processed.text
    assert processed.json()["queued_found"] >= 1
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM guest_notification_outbox
            WHERE id = :notification_id
              AND status = 'sent'
            """,
            {"notification_id": notification_id},
        )
        == 1
    )


def test_agent_harness_unauthorized_task_gets_403_and_audit(client):
    before = _count_denied("booking.review_public_request", FINANCE_EMAIL)
    response = client.post(
        "/agent-harness/tasks",
        json={
            "task_name": "create_reservation_request",
            "property_code": PROPERTY_CODE,
            "data": {
                "guest_name": "Blocked Agent Guest",
                "check_in_date": "2027-03-01",
                "check_out_date": "2027-03-02",
                "room_type": "Standard Room",
                "source": "agent_harness",
            },
        },
        headers=_headers(FINANCE_EMAIL),
    )
    _assert_permission_denied(response, "booking.review_public_request", FINANCE_EMAIL)
    assert _count_denied("booking.review_public_request", FINANCE_EMAIL) == before + 1


def test_fnb_pos_room_charge_posts_to_guest_folio_and_audit(client):
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="paid")
    response = client.post(
        "/food-costing/pos-sales",
        json={
            "property_code": PROPERTY_CODE,
            "outlet_name": "Main Restaurant",
            "menu_item_name": "QA Breakfast",
            "quantity_sold": 2,
            "selling_price": 250,
            "business_date": BUSINESS_DATE,
            "payment_method": "room_charge",
            "room_charge_booking_id": booking_id,
        },
        headers=_headers(ADMIN_EMAIL),
    )
    assert response.status_code == 200, response.text
    sale = response.json()
    assert float(sale["total_revenue"]) == 500.0
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM folio_transactions
            WHERE booking_id = :booking_id
              AND category = 'fnb'
              AND amount = 500
            """,
            {"booking_id": booking_id},
        )
        == 1
    )
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM folio_transactions
            WHERE booking_id = :booking_id
              AND category IN ('service_charge', 'tax')
            """,
            {"booking_id": booking_id},
        )
        == 2
    )
    assert (
        _db_scalar(
            """
            SELECT COUNT(*)
            FROM pms_audit_logs
            WHERE module = 'food_costing'
              AND action = 'fnb_charge_posted_to_folio'
              AND record_id = :sale_id
            """,
            {"sale_id": str(sale["id"])},
        )
        == 1
    )


def test_fnb_pos_room_charge_unauthorized_gets_403_and_audit(client):
    booking_id = _seed_booking("in_house", room_number="QA-101", payment_status="paid")
    before = _count_denied("fnb.post_room_charge", FRONTDESK_EMAIL)
    response = client.post(
        "/food-costing/pos-sales",
        json={
            "property_code": PROPERTY_CODE,
            "outlet_name": "Main Restaurant",
            "menu_item_name": "Blocked Room Charge",
            "quantity_sold": 1,
            "selling_price": 100,
            "business_date": BUSINESS_DATE,
            "payment_method": "room_charge",
            "room_charge_booking_id": booking_id,
        },
        headers=_headers(FRONTDESK_EMAIL),
    )
    _assert_permission_denied(response, "fnb.post_room_charge", FRONTDESK_EMAIL)
    assert _count_denied("fnb.post_room_charge", FRONTDESK_EMAIL) == before + 1


def test_global_property_scope_guard_isolates_known_properties(client):
    dre_email = "scope-dre001@guzo.test"
    xxx_email = "scope-xxx001@guzo.test"
    inactive_email = "scope-inactive@guzo.test"
    marker = uuid4().hex[:10]
    assert _TestingSessionLocal is not None
    booking_ids: dict[str, int] = {}

    with _TestingSessionLocal() as db:
        ensure_pms_security_tables(db, "DRE001")
        for email, property_code, is_active in [
            (dre_email, "DRE001", True),
            (xxx_email, "XXX001", True),
            (inactive_email, "DRE001", False),
        ]:
            db.execute(
                text(
                    """
                    INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                    VALUES (:email, :email, 'admin', :property_code, :is_active)
                    ON CONFLICT (email) DO UPDATE SET
                      role_key = 'admin', property_code = EXCLUDED.property_code,
                      is_active = EXCLUDED.is_active
                    """
                ),
                {"email": email, "property_code": property_code, "is_active": is_active},
            )

        for property_code in ["DRE001", "NN002", "XXX001"]:
            row = db.execute(
                text(
                    """
                    INSERT INTO bookings (
                      confirmation_id, hotel_id, guest_name, property_code, room_number,
                      room_type, check_in_date, check_out_date, booking_status,
                      payment_status, total_amount, total_revenue_etb, source, channel
                    )
                    SELECT :confirmation_id, id, :guest_name, :property_code, :room_number,
                           'Standard Room', :business_date, :business_date + 1,
                           'confirmed', 'pending', 100, 100, 'pytest', 'pytest'
                    FROM hotels WHERE property_code = :property_code
                    RETURNING id
                    """
                ),
                {
                    "confirmation_id": f"SCOPE-{marker}-{property_code}",
                    "guest_name": f"ScopeGuest-{marker}-{property_code}",
                    "property_code": property_code,
                    "room_number": f"S-{property_code}",
                    "business_date": date.fromisoformat(BUSINESS_DATE),
                },
            ).first()
            booking_ids[property_code] = int(row.id)
            db.execute(
                text(
                    """
                    INSERT INTO pms_audit_logs (
                      property_code, user_email, module, action, record_type, record_id,
                      old_value, new_value
                    ) VALUES (
                      :property_code, :email, 'scope_qa', 'scope_marker', 'booking',
                      :record_id, '{}'::jsonb, '{}'::jsonb
                    )
                    """
                ),
                {"property_code": property_code, "email": dre_email, "record_id": str(row.id)},
            )
        db.commit()

    def frontdesk(property_code: str, email: str):
        return client.get(
            "/frontdesk/bookings",
            params={"scope": "today", "date": BUSINESS_DATE, "property": property_code},
            headers=_headers(email),
        )

    dre_rows = frontdesk("DRE001", dre_email)
    assert dre_rows.status_code == 200, dre_rows.text
    assert dre_rows.json()
    assert {row["property_code"] for row in dre_rows.json()} == {"DRE001"}
    assert frontdesk("XXX001", dre_email).status_code == 403
    assert frontdesk("DRE001", xxx_email).status_code == 403
    assert frontdesk("NN002", xxx_email).status_code == 403

    xxx_rows = frontdesk("XXX001", xxx_email)
    assert xxx_rows.status_code == 200, xxx_rows.text
    assert {row["property_code"] for row in xxx_rows.json()} == {"XXX001"}

    for property_code in ["DRE001", "NN002", "XXX001"]:
        response = frontdesk(property_code, ADMIN_EMAIL)
        assert response.status_code == 200, response.text
        assert {row["property_code"] for row in response.json()} <= {property_code}

    cross_update = client.post(
        "/frontdesk/reservation-action",
        json={
            "booking_id": booking_ids["XXX001"],
            "property_code": "XXX001",
            "business_date": BUSINESS_DATE,
            "action": "add_trace",
        },
        headers=_headers(dre_email),
    )
    assert cross_update.status_code == 403

    audit_rows = client.get(
        "/admin/audit-logs",
        params={"property_code": "DRE001", "module": "scope_qa"},
        headers=_headers(dre_email),
    )
    assert audit_rows.status_code == 200, audit_rows.text
    assert {row["property_code"] for row in audit_rows.json()["audit_logs"]} <= {"DRE001"}

    search_rows = client.get(
        "/search/global",
        params={"property_code": "DRE001", "q": f"ScopeGuest-{marker}"},
        headers=_headers(dre_email),
    )
    assert search_rows.status_code == 200, search_rows.text
    search_titles = [item["title"] for group in search_rows.json()["groups"] for item in group["results"]]
    assert search_titles
    assert all("XXX001" not in title and "NN002" not in title for title in search_titles)

    assert client.get(
        "/reports/hotel/XXX001",
        params={"year": 2026, "month": 6},
        headers=_headers(dre_email),
    ).status_code == 403
    assert client.get(
        "/notifications/outbox",
        params={"property_code": "XXX001"},
        headers=_headers(dre_email),
    ).status_code == 403
    assert client.post(
        "/notifications/process-outbox",
        params={"property_code": "XXX001"},
        headers=_headers(dre_email),
    ).status_code == 403
    assert client.get(
        "/frontdesk/bookings",
        params={"scope": "today", "date": BUSINESS_DATE},
        headers=_headers(dre_email),
    ).status_code == 422
    assert frontdesk("DRE001", inactive_email).status_code == 403
    assert frontdesk("DRE001", "scope-unknown@guzo.test").status_code == 403


def test_finance_ledger_charge_payment_refund_and_idempotency(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    _open_controlled_cashier_shift(client, FINANCE_MANAGER_EMAIL)
    booking_id = _seed_booking("in_house", payment_status="pending", total_amount=500)
    marker = uuid4().hex

    charge = client.post(
        "/finance/folio/post-charge",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "category": "room",
            "description": "Immutable ledger room charge",
            "amount": 100,
            "currency": "ETB",
            "idempotency_key": f"charge-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert charge.status_code == 200, charge.text
    assert charge.json()["replayed"] is False

    payment_payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "payment_method": "cash",
        "description": "Immutable ledger cash payment",
        "amount": 40,
        "currency": "ETB",
        "idempotency_key": f"payment-{marker}",
    }
    payment = client.post("/finance/folio/post-payment", json=payment_payload, headers=_headers(FINANCE_EMAIL))
    replay = client.post("/finance/folio/post-payment", json=payment_payload, headers=_headers(FINANCE_EMAIL))
    assert payment.status_code == 200, payment.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"] is True
    assert replay.json()["ledger_transaction_id"] == payment.json()["ledger_transaction_id"]

    refund_payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "payment_method": "cash",
        "reason": "Approved duplicate payment refund",
        "amount": 10,
        "currency": "ETB",
        "idempotency_key": f"refund-{marker}",
    }
    refund = client.post("/finance/folio/refund", json=refund_payload, headers=_headers(FINANCE_MANAGER_EMAIL))
    refund_replay = client.post("/finance/folio/refund", json=refund_payload, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert refund.status_code == 200, refund.text
    assert refund_replay.status_code == 200, refund_replay.text
    assert refund_replay.json()["replayed"] is True

    assert _db_scalar(
        "SELECT COUNT(*) FROM finance_transactions WHERE property_code = :property_code AND idempotency_key = :key",
        {"property_code": PROPERTY_CODE, "key": f"payment-{marker}"},
    ) == 1
    assert _db_scalar(
        "SELECT COUNT(*) FROM pms_audit_logs WHERE action = 'finance_transaction_created' AND property_code = :property_code",
        {"property_code": PROPERTY_CODE},
    ) >= 3


def test_finance_ledger_void_and_correction_are_reversals(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_MANAGER_EMAIL)
    booking_id = _seed_booking("in_house", payment_status="pending", total_amount=500)
    marker = uuid4().hex
    charge = client.post(
        "/finance/folio/post-charge",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "category": "misc",
            "description": "Charge to void",
            "amount": 75,
            "currency": "ETB",
            "idempotency_key": f"void-source-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert charge.status_code == 200, charge.text
    original_ledger_id = charge.json()["ledger_transaction_id"]
    original_folio_id = charge.json()["charge_id"]

    voided = client.post(
        "/finance/folio/void-transaction",
        json={
            "property_code": PROPERTY_CODE,
            "transaction_id": original_folio_id,
            "business_date": BUSINESS_DATE,
            "reason": "Manager approved posting error",
            "idempotency_key": f"void-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert voided.status_code == 200, voided.text
    assert _db_scalar(
        "SELECT amount FROM finance_transactions WHERE id = :id",
        {"id": original_ledger_id},
    ) == Decimal("75.00")
    assert _db_scalar(
        "SELECT reversal_of_transaction_id FROM finance_transactions WHERE id = :id",
        {"id": voided.json()["ledger_reversal_transaction_id"]},
    ) == original_ledger_id
    assert _db_scalar(
        "SELECT voided_at FROM folio_transactions WHERE id = :id",
        {"id": original_folio_id},
    ) is None

    correction_source = client.post(
        "/finance/folio/post-charge",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "category": "misc",
            "description": "Charge to correct",
            "amount": 90,
            "currency": "ETB",
            "idempotency_key": f"correction-source-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    correction = client.post(
        "/finance/ledger/correct",
        json={
            "property_code": PROPERTY_CODE,
            "transaction_id": correction_source.json()["ledger_transaction_id"],
            "business_date": BUSINESS_DATE,
            "corrected_amount": 65,
            "reason": "Corrected approved amount",
            "idempotency_key": f"correction-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert correction.status_code == 200, correction.text
    assert _db_scalar(
        "SELECT amount FROM finance_transactions WHERE id = :id",
        {"id": correction.json()["corrected_transaction_id"]},
    ) == Decimal("65.00")
    assert _db_scalar(
        "SELECT reversal_of_transaction_id FROM finance_transactions WHERE id = :id",
        {"id": correction.json()["reversal_transaction_id"]},
    ) == correction_source.json()["ledger_transaction_id"]

    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        with pytest.raises(Exception):
            db.execute(
                text("UPDATE finance_transactions SET amount = 1 WHERE id = :id"),
                {"id": original_ledger_id},
            )
            db.commit()
        db.rollback()


def test_finance_ledger_property_isolation(client):
    marker = uuid4().hex
    xxx_email = f"finance-xxx-{marker}@guzo.test"
    assert _TestingSessionLocal is not None
    with _TestingSessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES (:email, :email, 'finance_manager', 'XXX001', TRUE)
                """
            ),
            {"email": xxx_email},
        )
        for property_code in ["DRE001", "NN002", "XXX001"]:
            db.execute(
                text(
                    """
                    INSERT INTO finance_transactions (
                      property_code, business_date, account_reference, transaction_type,
                      amount, currency, direction, created_by, idempotency_key, audit_reference
                    ) VALUES (
                      :property_code, :business_date, :account_reference, 'adjustment',
                      1, 'ETB', 'debit', :created_by, :idempotency_key, :audit_reference
                    )
                    """
                ),
                {
                    "property_code": property_code,
                    "business_date": date.fromisoformat(BUSINESS_DATE),
                    "account_reference": f"scope-{property_code}",
                    "created_by": ADMIN_EMAIL,
                    "idempotency_key": f"scope-{marker}-{property_code}",
                    "audit_reference": f"AUD-{marker}-{property_code}",
                },
            )
        db.commit()

    dre = client.get(
        "/finance/ledger",
        params={"property_code": "DRE001", "business_date": BUSINESS_DATE},
        headers=_headers(FINANCE_EMAIL),
    )
    assert dre.status_code == 200, dre.text
    assert {row["property_code"] for row in dre.json()} <= {"DRE001"}
    assert client.get("/finance/ledger", params={"property_code": "XXX001"}, headers=_headers(FINANCE_EMAIL)).status_code == 403
    assert client.get("/finance/ledger", params={"property_code": "DRE001"}, headers=_headers(xxx_email)).status_code == 403
    assert client.get("/finance/ledger", params={"property_code": "NN002"}, headers=_headers(xxx_email)).status_code == 403
    for property_code in ["DRE001", "NN002", "XXX001"]:
        response = client.get(
            "/finance/ledger",
            params={"property_code": property_code},
            headers=_headers(ADMIN_EMAIL),
        )
        assert response.status_code == 200, response.text
        assert {row["property_code"] for row in response.json()} <= {property_code}


def test_deposit_lifecycle_partial_full_refund_allocation_and_transfer(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    _open_controlled_cashier_shift(client, FINANCE_MANAGER_EMAIL)
    booking_id = _seed_booking("confirmed", payment_status="pending", total_amount=500)
    marker = uuid4().hex
    requested = client.post(
        "/finance/deposits/request",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "required_amount": 100,
            "requested_amount": 100,
            "currency": "ETB",
            "refundable": True,
            "reference": f"DEP-{marker}",
            "idempotency_key": f"deposit-request-{marker}",
        },
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert requested.status_code == 200, requested.text
    account_id = requested.json()["id"]
    assert requested.json()["status"] == "requested"

    partial_payload = {
        "property_code": PROPERTY_CODE,
        "business_date": BUSINESS_DATE,
        "amount": 40,
        "payment_method": "cash",
        "reference": f"PART-{marker}",
        "idempotency_key": f"deposit-partial-{marker}",
    }
    partial = client.post(f"/finance/deposits/{account_id}/receipt", json=partial_payload, headers=_headers(FINANCE_EMAIL))
    replay = client.post(f"/finance/deposits/{account_id}/receipt", json=partial_payload, headers=_headers(FINANCE_EMAIL))
    assert partial.status_code == 200, partial.text
    assert partial.json()["status"] == "partial"
    assert Decimal(str(partial.json()["paid_amount"])) == Decimal("40.00")
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    rejected = client.post(
        f"/finance/deposits/{account_id}/receipt",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "amount": 100,
            "payment_method": "cash",
            "reference": "must rollback",
            "idempotency_key": f"deposit-overreceipt-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert rejected.status_code == 409
    assert _db_scalar(
        "SELECT COUNT(*) FROM finance_transactions WHERE property_code=:property_code AND idempotency_key=:key",
        {"property_code": PROPERTY_CODE, "key": f"deposit-overreceipt-{marker}"},
    ) == 0

    refunded = client.post(
        f"/finance/deposits/{account_id}/refund",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "amount": 10,
            "payment_method": "cash",
            "reason": "Approved partial deposit refund",
            "idempotency_key": f"deposit-refund-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert refunded.status_code == 200, refunded.text

    full = client.post(
        f"/finance/deposits/{account_id}/receipt",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "amount": 60,
            "payment_method": "card",
            "reference": f"FULL-{marker}",
            "idempotency_key": f"deposit-full-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert full.status_code == 200, full.text
    assert full.json()["status"] == "paid"
    assert Decimal(str(full.json()["remaining_amount"])) == Decimal("0.00")

    allocated = client.post(
        f"/finance/deposits/{account_id}/allocate",
        json={"property_code": PROPERTY_CODE, "amount": 90, "idempotency_key": f"deposit-allocate-{marker}"},
        headers=_headers(FINANCE_EMAIL),
    )
    assert allocated.status_code == 200, allocated.text
    assert Decimal(str(allocated.json()["allocated_amount"])) == Decimal("90.00")

    transferred = client.post(
        f"/finance/deposits/{account_id}/transfer",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "amount": 90,
            "idempotency_key": f"deposit-transfer-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["status"] == "transferred"
    assert Decimal(str(transferred.json()["transferred_amount"])) == Decimal("90.00")
    assert _db_scalar(
        "SELECT COUNT(*) FROM deposit_events WHERE deposit_account_id=:id",
        {"id": account_id},
    ) == 6
    assert _db_scalar(
        "SELECT COUNT(*) FROM finance_transactions WHERE property_code=:property_code AND account_reference=:reference",
        {"property_code": PROPERTY_CODE, "reference": f"deposit:{account_id}"},
    ) == 4


def test_payment_receipt_split_overpayment_void_and_idempotency(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    _open_controlled_cashier_shift(client, FINANCE_MANAGER_EMAIL)
    booking_id = _seed_booking("in_house", payment_status="pending", total_amount=500)
    marker = uuid4().hex
    split_payload = {
        "property_code": PROPERTY_CODE,
        "booking_id": booking_id,
        "business_date": BUSINESS_DATE,
        "requested_amount": 100,
        "currency": "ETB",
        "reference": f"SPLIT-{marker}",
        "idempotency_key": f"split-payment-{marker}",
        "allocations": [
            {"payment_method": "cash", "amount": 40, "reference": f"CASH-{marker}"},
            {"payment_method": "card", "amount": 60, "reference": f"CARD-{marker}"},
        ],
    }
    split = client.post("/finance/payments/receipt", json=split_payload, headers=_headers(FINANCE_EMAIL))
    replay = client.post("/finance/payments/receipt", json=split_payload, headers=_headers(FINANCE_EMAIL))
    assert split.status_code == 200, split.text
    assert split.json()["status"] == "paid"
    assert len(split.json()["ledger_transaction_ids"]) == 2
    assert replay.status_code == 200 and replay.json()["replayed"] is True

    overpaid = client.post(
        "/finance/payments/receipt",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "requested_amount": 50,
            "currency": "ETB",
            "reference": f"OVER-{marker}",
            "idempotency_key": f"overpayment-{marker}",
            "allocations": [{"payment_method": "bank_transfer", "amount": 60, "reference": f"BANK-{marker}"}],
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert overpaid.status_code == 200, overpaid.text
    assert overpaid.json()["status"] == "overpaid"
    assert Decimal(str(overpaid.json()["overpayment_amount"])) == Decimal("10.00")

    original_payment_id = split.json()["ledger_transaction_ids"][0]
    refundable_payment_id = split.json()["ledger_transaction_ids"][1]
    refunded = client.post(
        "/finance/payments/refund",
        json={
            "property_code": PROPERTY_CODE,
            "original_transaction_id": refundable_payment_id,
            "business_date": BUSINESS_DATE,
            "amount": 10,
            "payment_method": "cash",
            "reason": "Approved partial tender refund",
            "idempotency_key": f"payment-refund-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert refunded.status_code == 200, refunded.text
    ineligible = client.post(
        "/finance/payments/refund",
        json={
            "property_code": PROPERTY_CODE,
            "original_transaction_id": refundable_payment_id,
            "business_date": BUSINESS_DATE,
            "amount": 55,
            "payment_method": "cash",
            "reason": "Exceeds remaining eligibility",
            "idempotency_key": f"payment-refund-too-much-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert ineligible.status_code == 409
    voided = client.post(
        "/finance/payments/void",
        json={
            "property_code": PROPERTY_CODE,
            "original_transaction_id": original_payment_id,
            "business_date": BUSINESS_DATE,
            "reason": "Supervisor approved duplicate tender void",
            "approved_by": FINANCE_MANAGER_EMAIL,
            "idempotency_key": f"payment-void-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert voided.status_code == 200, voided.text
    assert _db_scalar(
        "SELECT reversal_of_transaction_id FROM finance_transactions WHERE id=:id",
        {"id": voided.json()["reversal_transaction_id"]},
    ) == original_payment_id


def test_payment_deposit_cross_property_denial(client):
    booking_id = _seed_booking("confirmed", payment_status="pending", total_amount=200)
    marker = uuid4().hex
    requested = client.post(
        "/finance/deposits/request",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "required_amount": 50,
            "requested_amount": 50,
            "idempotency_key": f"scope-deposit-{marker}",
        },
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    assert requested.status_code == 200, requested.text
    account_id = requested.json()["id"]
    denied = client.post(
        f"/finance/deposits/{account_id}/receipt",
        json={
            "property_code": "XXX001",
            "business_date": BUSINESS_DATE,
            "amount": 10,
            "payment_method": "cash",
            "reference": "cross-property",
            "idempotency_key": f"cross-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert denied.status_code == 403
    assert client.get(
        "/finance/deposits",
        params={"property_code": "XXX001"},
        headers=_headers(FINANCE_EMAIL),
    ).status_code == 403


def test_nonrefundable_deposit_forfeiture_creates_adjustment(client):
    _reset_night_audit_state()
    _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    booking_id = _seed_booking("confirmed", payment_status="pending", total_amount=200)
    marker = uuid4().hex
    requested = client.post(
        "/finance/deposits/request",
        json={
            "property_code": PROPERTY_CODE,
            "booking_id": booking_id,
            "business_date": BUSINESS_DATE,
            "required_amount": 50,
            "requested_amount": 50,
            "refundable": False,
            "idempotency_key": f"forfeit-request-{marker}",
        },
        headers=_headers(RESERVATION_MANAGER_EMAIL),
    )
    account_id = requested.json()["id"]
    receipt = client.post(
        f"/finance/deposits/{account_id}/receipt",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "amount": 50,
            "payment_method": "card",
            "reference": f"FORFEIT-{marker}",
            "idempotency_key": f"forfeit-receipt-{marker}",
        },
        headers=_headers(FINANCE_EMAIL),
    )
    assert receipt.status_code == 200, receipt.text
    forfeited = client.post(
        f"/finance/deposits/{account_id}/forfeit",
        json={
            "property_code": PROPERTY_CODE,
            "business_date": BUSINESS_DATE,
            "reason": "No-show non-refundable deposit",
            "idempotency_key": f"forfeit-{marker}",
        },
        headers=_headers(FINANCE_MANAGER_EMAIL),
    )
    assert forfeited.status_code == 200, forfeited.text
    assert forfeited.json()["status"] == "forfeited"
    assert _db_scalar(
        "SELECT transaction_type FROM finance_transactions WHERE id=:id",
        {"id": forfeited.json()["finance_transaction_id"]},
    ) == "adjustment"


def test_cashier_shift_open_duplicate_payment_reconciliation_and_clean_close(client):
    _reset_night_audit_state()
    shift = _open_controlled_cashier_shift(client, FINANCE_EMAIL, opening_float=20)
    duplicate = client.post("/finance/cashier/shifts/open", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "cashier_name": "Duplicate", "opening_float": 0}, headers=_headers(FINANCE_EMAIL))
    assert duplicate.status_code == 409
    booking_id = _seed_booking("in_house", payment_status="pending", total_amount=100)
    payment = client.post("/finance/payments/receipt", json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE, "requested_amount": 100, "currency": "ETB", "idempotency_key": f"cashier-payment-{uuid4().hex}", "allocations": [{"payment_method": "cash", "amount": 100}]}, headers=_headers(FINANCE_EMAIL))
    assert payment.status_code == 200, payment.text
    assert _db_scalar("SELECT cashier_session_id FROM finance_transactions WHERE id=:id", {"id": payment.json()["ledger_transaction_ids"][0]}) == shift["id"]
    current = client.get("/finance/cashier/shifts/current", params={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE}, headers=_headers(FINANCE_EMAIL))
    assert Decimal(str(current.json()["shift"]["expected_by_method"]["cash"])) == Decimal("120.00")
    declared = client.post(f"/finance/cashier/shifts/{shift['id']}/declare", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "cash": 120, "card": 0, "bank_transfer": 0, "mobile_money": 0, "unassigned": 0}, headers=_headers(FINANCE_EMAIL))
    assert declared.status_code == 200 and declared.json()["status"] == "declared"
    assert Decimal(str(declared.json()["variance"])) == Decimal("0.00")
    closed = client.post(f"/finance/cashier/shifts/{shift['id']}/close", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE}, headers=_headers(FINANCE_EMAIL))
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
    assert closed.json()["closure_report"]["expected_total"] == "120.00"
    blocked = client.post("/finance/payments/receipt", json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE, "requested_amount": 1, "currency": "ETB", "idempotency_key": f"closed-shift-{uuid4().hex}", "allocations": [{"payment_method": "cash", "amount": 1}]}, headers=_headers(FINANCE_EMAIL))
    assert blocked.status_code == 409


def test_cashier_payment_requires_open_shift_and_variance_requires_approval(client):
    _reset_night_audit_state()
    booking_id = _seed_booking("in_house", payment_status="pending", total_amount=50)
    no_shift_key = f"no-shift-{uuid4().hex}"
    no_shift = client.post("/finance/payments/receipt", json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE, "requested_amount": 10, "currency": "ETB", "idempotency_key": no_shift_key, "allocations": [{"payment_method": "cash", "amount": 10}]}, headers=_headers(FINANCE_EMAIL))
    assert no_shift.status_code == 409
    assert _db_scalar("SELECT COUNT(*) FROM finance_transactions WHERE idempotency_key=:key", {"key": f"{no_shift_key}:0"}) == 0
    shift = _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    declared = client.post(f"/finance/cashier/shifts/{shift['id']}/declare", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "cash": 5, "card": 0, "bank_transfer": 0, "mobile_money": 0, "unassigned": 0}, headers=_headers(FINANCE_EMAIL))
    assert declared.status_code == 200 and declared.json()["status"] == "approval_required"
    denied_close = client.post(f"/finance/cashier/shifts/{shift['id']}/close", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE}, headers=_headers(FINANCE_EMAIL))
    assert denied_close.status_code == 409
    requested = client.post(f"/finance/cashier/shifts/{shift['id']}/request-approval", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "reason": "Drawer counted twice"}, headers=_headers(FINANCE_EMAIL))
    assert requested.status_code == 200 and requested.json()["status"] == "approval_requested"
    approved = client.post(f"/finance/cashier/shifts/{shift['id']}/approve", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "reason": "Manager verified drawer count"}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    closed = client.post(f"/finance/cashier/shifts/{shift['id']}/close", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE}, headers=_headers(FINANCE_EMAIL))
    assert closed.status_code == 200


def test_cashier_shift_property_and_closed_business_date_safety(client):
    _reset_night_audit_state()
    shift = _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    cross_property = client.get(f"/finance/cashier/shifts/{shift['id']}/report", params={"property_code": "XXX001"}, headers=_headers(FINANCE_EMAIL))
    assert cross_property.status_code == 403
    from guzo_backend.services.business_date_lock_service import lock_business_date
    assert _TestingSessionLocal is not None
    locked_day = date.fromisoformat(BUSINESS_DATE) + timedelta(days=1)
    with _TestingSessionLocal() as db:
        lock_business_date(db, property_code=PROPERTY_CODE, business_date=locked_day, closed_by=NIGHT_AUDIT_EMAIL, notes="cashier safety test")
        db.commit()
    blocked = client.post("/finance/cashier/shifts/open", json={"property_code": PROPERTY_CODE, "business_date": locked_day.isoformat(), "cashier_name": FINANCE_EMAIL, "opening_float": 0}, headers=_headers(FINANCE_EMAIL))
    assert blocked.status_code == 409


def _create_ar_company(client, *, credit_limit: float = 1000, status: str = "active", allow_direct_bill: bool = True):
    marker = uuid4().hex[:8].upper()
    response = client.post("/finance/ar/companies", json={"property_code": PROPERTY_CODE, "company_name": f"QA Company {marker}", "account_code": f"QA-{marker}", "billing_contact": "AR Contact", "email": f"ar-{marker.lower()}@example.com", "phone": "+251900000000", "address": "Addis Ababa", "tax_id": f"TIN-{marker}", "credit_limit": credit_limit, "status": status, "payment_terms": 30, "allow_direct_bill": allow_direct_bill}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert response.status_code == 200, response.text
    return response.json()


def _create_ar_folio(client, amount: float = 100):
    booking_id = _seed_booking("checked_out", payment_status="pending", total_amount=amount)
    charge = client.post("/finance/folio/post-charge", json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "business_date": BUSINESS_DATE, "amount": amount, "category": "room", "description": "AR transfer test", "currency": "ETB", "idempotency_key": f"ar-charge-{uuid4().hex}"}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert charge.status_code == 200, charge.text
    return booking_id


def _transfer_ar_folio(client, company_id: int, booking_id: int, override: str | None = None):
    return client.post("/finance/ar/transfers", json={"property_code": PROPERTY_CODE, "booking_id": booking_id, "company_account_id": company_id, "business_date": BUSINESS_DATE, "tax": 0, "manager_override_reason": override, "idempotency_key": f"ar-transfer-{uuid4().hex}"}, headers=_headers(FINANCE_MANAGER_EMAIL))


def test_ar_company_credit_controls_and_inactive_accounts(client):
    active = _create_ar_company(client, credit_limit=50)
    assert active["status"] == "active" and active["allow_direct_bill"] is True
    assert _db_scalar("SELECT COUNT(*) FROM pms_audit_logs WHERE action='ar_company_created' AND record_id=:id", {"id": str(active["id"])}) == 1
    booking_id = _create_ar_folio(client, 100)
    limited = _transfer_ar_folio(client, active["id"], booking_id)
    assert limited.status_code == 409 and "credit limit" in limited.text
    override = _transfer_ar_folio(client, active["id"], booking_id, "Finance manager approved temporary excess")
    assert override.status_code == 200, override.text
    assert override.json()["override_reason"] == "Finance manager approved temporary excess"
    held = _create_ar_company(client, status="on_hold")
    held_booking = _create_ar_folio(client, 25)
    blocked = _transfer_ar_folio(client, held["id"], held_booking, "Attempted override")
    assert blocked.status_code == 409


def test_ar_transfer_is_atomic_and_creates_invoice_and_ledger(client):
    company_account = _create_ar_company(client)
    booking_id = _create_ar_folio(client, 125)
    transferred = _transfer_ar_folio(client, company_account["id"], booking_id)
    assert transferred.status_code == 200, transferred.text
    body = transferred.json()
    assert body["status"] == "issued" and Decimal(str(body["balance_due"])) == Decimal("125.00")
    assert _db_scalar("SELECT transaction_type FROM finance_transactions WHERE id=:id", {"id": body["ledger_transaction_id"]}) == "transfer"
    assert Decimal(str(_db_scalar("SELECT current_balance FROM ar_company_accounts WHERE id=:id", {"id": company_account["id"]}))) == Decimal("125.00")

    rollback_company = _create_ar_company(client)
    rollback_booking = _create_ar_folio(client, 33)
    with _TestingSessionLocal() as db:
        db.execute(text("CREATE OR REPLACE FUNCTION fail_ar_invoice_test() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'forced AR failure'; END; $$ LANGUAGE plpgsql"))
        db.execute(text("CREATE TRIGGER fail_ar_invoice_insert BEFORE INSERT ON ar_invoices FOR EACH ROW EXECUTE FUNCTION fail_ar_invoice_test()")); db.commit()
    failed_key = f"ar-forced-{uuid4().hex}"
    failed = client.post("/finance/ar/transfers", json={"property_code": PROPERTY_CODE, "booking_id": rollback_booking, "company_account_id": rollback_company["id"], "business_date": BUSINESS_DATE, "tax": 0, "idempotency_key": failed_key}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert failed.status_code == 500
    with _TestingSessionLocal() as db:
        db.execute(text("DROP TRIGGER fail_ar_invoice_insert ON ar_invoices")); db.execute(text("DROP FUNCTION fail_ar_invoice_test()")); db.commit()
    assert _db_scalar("SELECT COUNT(*) FROM finance_transactions WHERE idempotency_key=:key", {"key": failed_key}) == 0
    assert Decimal(str(_db_scalar("SELECT current_balance FROM ar_company_accounts WHERE id=:id", {"id": rollback_company["id"]}))) == Decimal("0.00")


def test_ar_partial_full_payment_cashier_and_overpayment(client):
    _reset_night_audit_state()
    account = _create_ar_company(client)
    booking_id = _create_ar_folio(client, 100)
    invoice_body = _transfer_ar_folio(client, account["id"], booking_id).json()
    no_shift = client.post("/finance/ar/payments", json={"property_code": PROPERTY_CODE, "company_account_id": account["id"], "business_date": BUSINESS_DATE, "amount": 40, "currency": "ETB", "payment_method": "cash", "channel": "front_desk", "invoice_ids": [invoice_body["id"]], "idempotency_key": f"ar-no-shift-{uuid4().hex}"}, headers=_headers(FINANCE_EMAIL))
    assert no_shift.status_code == 409
    shift = _open_controlled_cashier_shift(client, FINANCE_EMAIL)
    partial = client.post("/finance/ar/payments", json={"property_code": PROPERTY_CODE, "company_account_id": account["id"], "business_date": BUSINESS_DATE, "amount": 40, "currency": "ETB", "payment_method": "cash", "channel": "front_desk", "invoice_ids": [invoice_body["id"]], "idempotency_key": f"ar-partial-{uuid4().hex}"}, headers=_headers(FINANCE_EMAIL))
    assert partial.status_code == 200 and Decimal(str(partial.json()["allocated_amount"])) == Decimal("40.00")
    assert partial.json()["cashier_session_id"] == shift["id"]
    assert _db_scalar("SELECT status FROM ar_invoices WHERE id=:id", {"id": invoice_body["id"]}) == "partially_paid"
    full = client.post("/finance/ar/payments", json={"property_code": PROPERTY_CODE, "company_account_id": account["id"], "business_date": BUSINESS_DATE, "amount": 70, "currency": "ETB", "payment_method": "bank_transfer", "channel": "back_office", "invoice_ids": [invoice_body["id"]], "idempotency_key": f"ar-full-{uuid4().hex}"}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert full.status_code == 200
    assert Decimal(str(full.json()["allocated_amount"])) == Decimal("60.00") and Decimal(str(full.json()["unapplied_amount"])) == Decimal("10.00")
    assert _db_scalar("SELECT status FROM ar_invoices WHERE id=:id", {"id": invoice_body["id"]}) == "paid"


def test_ar_invoice_void_aging_property_and_locked_date(client):
    account = _create_ar_company(client)
    booking_id = _create_ar_folio(client, 80)
    transferred = _transfer_ar_folio(client, account["id"], booking_id).json()
    voided = client.post(f"/finance/ar/invoices/{transferred['id']}/void", json={"property_code": PROPERTY_CODE, "business_date": BUSINESS_DATE, "reason": "Approved billing cancellation", "idempotency_key": f"ar-void-{uuid4().hex}"}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert voided.status_code == 200, voided.text
    assert voided.json()["original_transaction_id"] == transferred["ledger_transaction_id"]
    assert _db_scalar("SELECT reversal_of_transaction_id FROM finance_transactions WHERE id=:id", {"id": voided.json()["reversal_transaction_id"]}) == transferred["ledger_transaction_id"]
    assert _db_scalar("SELECT transaction_type FROM finance_transactions WHERE id=:id", {"id": transferred["ledger_transaction_id"]}) == "transfer"

    aging_account = _create_ar_company(client)
    aging_booking = _create_ar_folio(client, 45)
    aging_invoice = _transfer_ar_folio(client, aging_account["id"], aging_booking).json()
    with _TestingSessionLocal() as db:
        db.execute(text("UPDATE ar_invoices SET due_date=:due WHERE id=:id"), {"due": date.fromisoformat(BUSINESS_DATE)-timedelta(days=45), "id": aging_invoice["id"]}); db.commit()
    report = client.get("/finance/ar/aging", params={"property_code": PROPERTY_CODE, "as_of": BUSINESS_DATE}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert report.status_code == 200 and Decimal(str(report.json()["buckets"]["31_60"])) >= Decimal("45.00")
    assert client.get("/finance/ar/companies", params={"property_code": "XXX001"}, headers=_headers(FINANCE_EMAIL)).status_code == 403

    from guzo_backend.services.business_date_lock_service import lock_business_date
    locked_day = date.fromisoformat(BUSINESS_DATE)+timedelta(days=3)
    with _TestingSessionLocal() as db:
        lock_business_date(db,property_code=PROPERTY_CODE,business_date=locked_day,closed_by=NIGHT_AUDIT_EMAIL,notes="AR lock test");db.commit()
    locked = client.post("/finance/ar/payments", json={"property_code": PROPERTY_CODE, "company_account_id": aging_account["id"], "business_date": locked_day.isoformat(), "amount": 1, "currency": "ETB", "payment_method": "bank_transfer", "channel": "back_office", "idempotency_key": f"ar-locked-{uuid4().hex}"}, headers=_headers(FINANCE_MANAGER_EMAIL))
    assert locked.status_code == 409
