# guzo_backend/scripts/create_housekeeping_status_table.py

from sqlalchemy import text
from guzo_backend.core.postgres_db import get_db_connection


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS housekeeping_status (
    id SERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    property_code VARCHAR(50) NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    hk_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT housekeeping_status_unique_per_day
        UNIQUE (business_date, property_code, room_number)
);
"""


def main() -> None:
    print("[HK] Creating housekeeping_status table if not exists...")
    with get_db_connection() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
    print("[HK] Done. housekeeping_status table is ready.")


if __name__ == "__main__":
    main()
