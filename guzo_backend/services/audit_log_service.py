from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def record_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    hotel_id: int | None = None,
    property_code: str | None = None,
    business_date: date | str | None = None,
    performed_by: str = "frontdesk",
    details: dict[str, Any] | None = None,
) -> None:
    """
    Record an operational audit event without letting audit logging break the
    guest workflow. The table is intentionally small and can be expanded by a
    future migration as the enterprise PMS schema matures.
    """
    db.execute(
        text(
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
    )
    db.execute(
        text(
            """
            INSERT INTO audit_logs (
                hotel_id,
                property_code,
                action,
                entity_type,
                entity_id,
                business_date,
                performed_by,
                details
            )
            VALUES (
                :hotel_id,
                :property_code,
                :action,
                :entity_type,
                :entity_id,
                :business_date,
                :performed_by,
                CAST(:details AS jsonb)
            )
            """
        ),
        {
            "hotel_id": hotel_id,
            "property_code": property_code,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "business_date": business_date,
            "performed_by": performed_by,
            "details": json.dumps(details or {}),
        },
    )
