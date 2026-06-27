"""Add production city ledger and accounts receivable subledger.

Revision ID: 20260620_0029
Revises: 20260620_0028
"""
from alembic import op

revision = "20260620_0029"
down_revision = "20260620_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS transferred_to TEXT")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS transfer_reason TEXT")
    op.execute("ALTER TABLE folios ADD COLUMN IF NOT EXISTS transferred_at TIMESTAMPTZ")
    op.execute("""
      CREATE TABLE IF NOT EXISTS ar_company_accounts (
        id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL,
        company_name VARCHAR(180) NOT NULL, account_code VARCHAR(60) NOT NULL,
        billing_contact VARCHAR(180), email VARCHAR(255), phone VARCHAR(80), address TEXT, tax_id VARCHAR(100),
        credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0, current_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','closed')),
        payment_terms INTEGER NOT NULL DEFAULT 30 CHECK(payment_terms >= 0), allow_direct_bill BOOLEAN NOT NULL DEFAULT TRUE,
        created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(property_code, account_code)
      );
      CREATE TABLE IF NOT EXISTS ar_invoices (
        id BIGSERIAL PRIMARY KEY, invoice_number VARCHAR(80) NOT NULL, property_code VARCHAR(20) NOT NULL,
        company_account_id BIGINT NOT NULL REFERENCES ar_company_accounts(id), folio_id BIGINT, booking_id BIGINT,
        guest_reference VARCHAR(255), issue_date DATE NOT NULL, due_date DATE NOT NULL,
        subtotal NUMERIC(18,2) NOT NULL, tax NUMERIC(18,2) NOT NULL DEFAULT 0, total NUMERIC(18,2) NOT NULL,
        balance_due NUMERIC(18,2) NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'issued'
          CHECK(status IN ('draft','issued','partially_paid','paid','voided','overdue')),
        transfer_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id), override_reason TEXT,
        created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), voided_at TIMESTAMPTZ,
        UNIQUE(property_code, invoice_number), UNIQUE(property_code, folio_id)
      );
      CREATE TABLE IF NOT EXISTS ar_invoice_sources (
        id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id),
        finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id), source_type VARCHAR(50) NOT NULL,
        amount NUMERIC(18,2) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS ar_payments (
        id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, company_account_id BIGINT NOT NULL REFERENCES ar_company_accounts(id),
        business_date DATE NOT NULL, amount NUMERIC(18,2) NOT NULL CHECK(amount > 0), currency VARCHAR(10) NOT NULL,
        payment_method VARCHAR(80) NOT NULL, reference VARCHAR(255), channel VARCHAR(30) NOT NULL,
        allocated_amount NUMERIC(18,2) NOT NULL DEFAULT 0, unapplied_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
        finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id), cashier_session_id BIGINT REFERENCES cashier_sessions(id),
        idempotency_key VARCHAR(180) NOT NULL, created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(property_code, idempotency_key)
      );
      CREATE TABLE IF NOT EXISTS ar_payment_allocations (
        id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, payment_id BIGINT NOT NULL REFERENCES ar_payments(id),
        invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id), amount NUMERIC(18,2) NOT NULL CHECK(amount > 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(payment_id, invoice_id)
      );
      CREATE TABLE IF NOT EXISTS ar_adjustments (
        id BIGSERIAL PRIMARY KEY, property_code VARCHAR(20) NOT NULL, invoice_id BIGINT NOT NULL REFERENCES ar_invoices(id),
        amount NUMERIC(18,2) NOT NULL CHECK(amount > 0), direction VARCHAR(10) NOT NULL CHECK(direction IN ('debit','credit')),
        reason TEXT NOT NULL, finance_transaction_id BIGINT NOT NULL REFERENCES finance_transactions(id),
        created_by VARCHAR(255) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS ix_ar_company_property ON ar_company_accounts(property_code,status);
      CREATE INDEX IF NOT EXISTS ix_ar_invoice_property_status ON ar_invoices(property_code,company_account_id,status,due_date);
      CREATE INDEX IF NOT EXISTS ix_ar_payment_property_date ON ar_payments(property_code,business_date);
    """)


def downgrade() -> None:
    pass
