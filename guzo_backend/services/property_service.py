from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


DEFAULT_PROPERTY_ROWS = [
    {
        "name": "Dream Big Hotel",
        "property_code": "DRE001",
        "address": "Bole Road",
        "city": "Addis Ababa",
        "country": "Ethiopia",
        "timezone": "Africa/Addis_Ababa",
        "currency": "ETB",
        "phone": "+251 11 000 0000",
        "email": "admin@dreambig.local",
        "is_active": True,
        "onboarding_status": "complete",
    },
    {
        "name": "N&N Hotel",
        "property_code": "NN002",
        "address": "Airport District",
        "city": "Addis Ababa",
        "country": "Ethiopia",
        "timezone": "Africa/Addis_Ababa",
        "currency": "ETB",
        "phone": "+251 11 000 0001",
        "email": "admin@nnhotel.local",
        "is_active": True,
        "onboarding_status": "in_progress",
    },
]


def normalize_property_code(property_code: str) -> str:
    return "".join(property_code.strip().upper().split())


def ensure_property_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS hotel_properties (
                id SERIAL PRIMARY KEY,
                name VARCHAR(180) NOT NULL,
                property_code VARCHAR(20) NOT NULL UNIQUE,
                address TEXT NOT NULL DEFAULT '',
                city VARCHAR(120) NOT NULL DEFAULT '',
                country VARCHAR(120) NOT NULL DEFAULT '',
                timezone VARCHAR(100) NOT NULL DEFAULT 'Africa/Addis_Ababa',
                currency VARCHAR(10) NOT NULL DEFAULT 'ETB',
                phone VARCHAR(80) NOT NULL DEFAULT '',
                email VARCHAR(255) NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                onboarding_status VARCHAR(40) NOT NULL DEFAULT 'not_started',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_hotel_properties_active ON hotel_properties (is_active)"))
    for row in DEFAULT_PROPERTY_ROWS:
        db.execute(
            text(
                """
                INSERT INTO hotel_properties (
                    name, property_code, address, city, country, timezone,
                    currency, phone, email, is_active, onboarding_status
                )
                VALUES (
                    :name, :property_code, :address, :city, :country, :timezone,
                    :currency, :phone, :email, :is_active, :onboarding_status
                )
                ON CONFLICT (property_code) DO NOTHING
                """
            ),
            row,
        )
    db.flush()


def property_row_to_api(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": data["id"],
        "name": data["name"],
        "code": data["property_code"],
        "address": data.get("address") or "",
        "city": data.get("city") or "",
        "country": data.get("country") or "",
        "timezone": data.get("timezone") or "Africa/Addis_Ababa",
        "currency": data.get("currency") or "ETB",
        "phone": data.get("phone") or "",
        "email": data.get("email") or "",
        "isActive": bool(data.get("is_active")),
        "onboardingStatus": data.get("onboarding_status") or "not_started",
        "createdAt": data.get("created_at").isoformat() if data.get("created_at") else None,
        "updatedAt": data.get("updated_at").isoformat() if data.get("updated_at") else None,
    }


def list_properties(db: Session) -> list[dict[str, Any]]:
    ensure_property_table(db)
    rows = db.execute(
        text(
            """
            SELECT *
            FROM hotel_properties
            ORDER BY is_active DESC, name ASC, id ASC
            """
        )
    ).mappings().all()
    return [property_row_to_api(row) for row in rows]


def get_property_by_id(db: Session, property_id: int) -> dict[str, Any] | None:
    ensure_property_table(db)
    row = db.execute(
        text("SELECT * FROM hotel_properties WHERE id = :property_id"),
        {"property_id": property_id},
    ).mappings().first()
    return dict(row) if row else None


def get_property_by_code(db: Session, property_code: str) -> dict[str, Any] | None:
    ensure_property_table(db)
    row = db.execute(
        text("SELECT * FROM hotel_properties WHERE property_code = :property_code"),
        {"property_code": normalize_property_code(property_code)},
    ).mappings().first()
    return dict(row) if row else None
