from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def normalize_property_code(property_code: str | None) -> str | None:
    return property_code.strip().upper() if property_code else None


def ensure_business_date_lock_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS business_date_locks (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                business_date DATE NOT NULL,
                status VARCHAR(50) DEFAULT 'locked',
                locked_by VARCHAR(150),
                locked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                closed_by VARCHAR(150),
                closed_at TIMESTAMPTZ,
                reopened_by VARCHAR(150),
                reopened_at TIMESTAMPTZ,
                notes TEXT,
                UNIQUE(property_code, business_date)
            )
            """
        )
    )
    for statement in [
        "ALTER TABLE business_date_locks ADD COLUMN IF NOT EXISTS closed_by VARCHAR(150)",
        "ALTER TABLE business_date_locks ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ",
        "ALTER TABLE business_date_locks ADD COLUMN IF NOT EXISTS reopened_by VARCHAR(150)",
        "ALTER TABLE business_date_locks ADD COLUMN IF NOT EXISTS reopened_at TIMESTAMPTZ",
    ]:
        db.execute(text(statement))


def get_business_date_lock(db: Session, property_code: str, business_date: date):
    ensure_business_date_lock_table(db)
    return db.execute(
        text(
            """
            SELECT id, property_code, business_date, status, locked_by, locked_at,
                   closed_by, closed_at, reopened_by, reopened_at, notes
            FROM business_date_locks
            WHERE property_code = :property_code
              AND business_date = :business_date
              AND LOWER(COALESCE(status, 'locked')) = 'locked'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {
            "property_code": normalize_property_code(property_code),
            "business_date": business_date,
        },
    ).mappings().first()


def is_business_date_locked(db: Session, property_code: str, business_date: date | None) -> bool:
    if business_date is None:
        return False
    return bool(get_business_date_lock(db, property_code, business_date))


def assert_business_date_editable(
    db: Session,
    *,
    property_code: str,
    business_date: date | None,
    module: str,
    action: str,
) -> None:
    if not business_date:
        return
    lock = get_business_date_lock(db, property_code, business_date)
    if not lock:
        return
    raise HTTPException(
        status_code=409,
        detail=(
            f"Business date {business_date.isoformat()} is locked by Night Audit. "
            f"{module}.{action} requires manager/admin adjustment workflow."
        ),
    )


def lock_business_date(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    closed_by: str | None,
    notes: str | None = None,
) -> None:
    ensure_business_date_lock_table(db)
    db.execute(
        text(
            """
            INSERT INTO business_date_locks (
                property_code, business_date, status, locked_by, closed_by, closed_at, notes
            )
            VALUES (
                :property_code, :business_date, 'locked', :closed_by, :closed_by, NOW(), :notes
            )
            ON CONFLICT (property_code, business_date) DO UPDATE
            SET status = 'locked',
                locked_by = EXCLUDED.locked_by,
                locked_at = NOW(),
                closed_by = EXCLUDED.closed_by,
                closed_at = COALESCE(business_date_locks.closed_at, NOW()),
                notes = EXCLUDED.notes
            """
        ),
        {
            "property_code": normalize_property_code(property_code),
            "business_date": business_date,
            "closed_by": closed_by,
            "notes": notes,
        },
    )


def reopen_business_date(
    db: Session,
    *,
    property_code: str,
    business_date: date,
    reopened_by: str | None,
    reason: str | None,
) -> None:
    ensure_business_date_lock_table(db)
    db.execute(
        text(
            """
            UPDATE business_date_locks
            SET status = 'reopened',
                reopened_by = :reopened_by,
                reopened_at = NOW(),
                notes = NULLIF(CONCAT_WS(E'\n', NULLIF(notes, ''), :reason), '')
            WHERE property_code = :property_code
              AND business_date = :business_date
            """
        ),
        {
            "property_code": normalize_property_code(property_code),
            "business_date": business_date,
            "reopened_by": reopened_by,
            "reason": reason,
        },
    )
