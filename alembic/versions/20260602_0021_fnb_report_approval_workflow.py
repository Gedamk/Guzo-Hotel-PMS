"""Add F&B report approval workflow.

Revision ID: 20260602_0021
Revises: 20260602_0020
Create Date: 2026-06-07
"""

from __future__ import annotations

from alembic import op


revision = "20260602_0021"
down_revision = "20260602_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fnb_report_approvals (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            report_period VARCHAR(20) NOT NULL,
            report_start_date DATE NOT NULL,
            report_end_date DATE NOT NULL,
            status VARCHAR(40) DEFAULT 'draft',
            prepared_by VARCHAR(150),
            prepared_at TIMESTAMP,
            finance_reviewed_by VARCHAR(150),
            finance_reviewed_at TIMESTAMP,
            fnb_approved_by VARCHAR(150),
            fnb_approved_at TIMESTAMP,
            gm_approved_by VARCHAR(150),
            gm_approved_at TIMESTAMP,
            locked_at TIMESTAMP,
            override_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE(property_code, report_period, report_start_date, report_end_date)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_fnb_report_approvals_property_status
        ON fnb_report_approvals(property_code, status)
        """
    )

    role_permissions = {
        "general_manager": [
            "fnb.submit_report",
            "fnb.finance_review_report",
            "fnb.approve_report",
            "fnb.gm_lock_report",
            "fnb.override_report",
        ],
        "admin": [
            "fnb.submit_report",
            "fnb.finance_review_report",
            "fnb.approve_report",
            "fnb.gm_lock_report",
            "fnb.override_report",
        ],
        "finance_cashier": ["fnb.finance_review_report"],
        "fb_controller": ["fnb.submit_report", "fnb.approve_report"],
    }
    for role_key, permissions in role_permissions.items():
        for permission_key in permissions:
            op.execute(
                f"""
                INSERT INTO pms_role_permissions(role_key, permission_key, allowed)
                VALUES ('{role_key}', '{permission_key}', TRUE)
                ON CONFLICT (role_key, permission_key) DO NOTHING
                """
            )


def downgrade() -> None:
    pass
