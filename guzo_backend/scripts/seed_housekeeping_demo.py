# guzo_backend/scripts/seed_housekeeping_demo.py

from datetime import date

from sqlalchemy import text  # type: ignore

from guzo_backend.core.postgres_db import get_db_connection


def main() -> None:
    """
    Seed demo housekeeping_status rows for the Housekeeping Board.

    Uses get_db_connection(), which returns the same SQLAlchemy-style
    connection the rest of the backend uses. We call conn.execute(...)
    instead of using .cursor().
    """
    business_date = date(2025, 12, 2)

    demo_rows = [
        # Dream Big Hotel (DRE001)
        ("DRE001", "200", "occupied_clean"),   # existing occupied room
        ("DRE001", "201", "vacant_clean"),
        ("DRE001", "202", "vacant_dirty"),
        ("DRE001", "203", "out_of_order"),
        ("DRE001", "204", "in_service"),

        # N&N Luxury Hotel (N&N002)
        ("N&N002", "301", "vacant_clean"),
        ("N&N002", "302", "vacant_dirty"),
        ("N&N002", "303", "occupied_clean"),
    ]

    sql = text(
        """
        INSERT INTO housekeeping_status (
            business_date,
            property_code,
            room_number,
            hk_status
        )
        VALUES (:business_date, :property_code, :room_number, :hk_status)
        ON CONFLICT (business_date, property_code, room_number)
        DO UPDATE SET
            hk_status = EXCLUDED.hk_status,
            updated_at = now()
        """
    )

    try:
        with get_db_connection() as conn:
            for prop_code, room_number, hk_status in demo_rows:
                conn.execute(
                    sql,
                    {
                        "business_date": business_date,
                        "property_code": prop_code,
                        "room_number": room_number,
                        "hk_status": hk_status,
                    },
                )
            conn.commit()
        print("[SEED] Done. Demo HK rows inserted for", business_date)
    except Exception as e:
        print("[SEED] Error seeding housekeeping demo rows:", e)


if __name__ == "__main__":
    main()
