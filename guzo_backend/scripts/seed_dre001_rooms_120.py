# guzo_backend/scripts/seed_dre001_rooms_120.py

from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import bindparam, text  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

from guzo_backend.core.postgres_db import get_db_connection


ROOM_TYPES = [
    "Single Room",
    "Double Room",
    "Twin Room",
    "Queen Room",
    "King Room",
    "Standard Room",
    "Deluxe Room",
    "Superior Room",
    "Executive Room",
    "Family Room",
    "Connecting Rooms",
    "Accessible Room",
    "Suite",
    "Junior Suite",
    "Executive Suite",
    "Presidential Suite",
    "Villa / Bungalow",
    "Dormitory / Shared Room",
]

TOTAL_FLOORS = 10
ROOMS_PER_FLOOR = 12


def build_rooms(hotel_id: int) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    type_index = 0

    for floor in range(1, TOTAL_FLOORS + 1):
        for room in range(1, ROOMS_PER_FLOOR + 1):
            rows.append(
                {
                    "hotel_id": hotel_id,
                    "property_code": "DRE001",
                    "room_number": f"{floor}{room:02d}",
                    "room_type": ROOM_TYPES[type_index % len(ROOM_TYPES)],
                    "floor": str(floor),
                    "status": "available",
                }
            )
            type_index += 1

    return rows


def main() -> None:
    """
    Configure Dream Big Hotel (DRE001) with 120 rooms.

    This creates or updates 12 rooms per floor across floors 1-10:
    101-112, 201-212, ... 1001-1012.
    """
    hotel_total_sql = text(
        "ALTER TABLE hotels ADD COLUMN IF NOT EXISTS total_rooms INTEGER"
    )
    hotel_upsert_sql = text(
        """
        INSERT INTO hotels (
            property_code,
            name,
            total_rooms
        )
        VALUES (
            :property_code,
            :name,
            :total_rooms
        )
        ON CONFLICT (property_code)
        DO UPDATE SET
            name = EXCLUDED.name,
            total_rooms = EXCLUDED.total_rooms
        """
    )
    create_sql = text(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            room_number VARCHAR(20) NOT NULL,
            room_type VARCHAR(50) NOT NULL,
            floor VARCHAR(20),
            status VARCHAR(20) DEFAULT 'available',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    index_sql = text(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rooms_property_room
        ON rooms (property_code, room_number)
        """
    )
    upsert_sql = text(
        """
        INSERT INTO rooms (
            hotel_id,
            property_code,
            room_number,
            room_type,
            floor,
            status
        )
        VALUES (
            :hotel_id,
            :property_code,
            :room_number,
            :room_type,
            :floor,
            :status
        )
        ON CONFLICT (property_code, room_number)
        DO UPDATE SET
            hotel_id = EXCLUDED.hotel_id,
            room_type = EXCLUDED.room_type,
            floor = EXCLUDED.floor,
            status = COALESCE(rooms.status, EXCLUDED.status)
        """
    )
    hotel_id_sql = text(
        """
        SELECT id
        FROM hotels
        WHERE property_code = :property_code
        LIMIT 1
        """
    )
    count_sql = text(
        "SELECT COUNT(*) FROM rooms WHERE property_code = :property_code"
    )
    prune_sql = text(
        """
        DELETE FROM rooms
        WHERE property_code = :property_code
          AND room_number NOT IN :room_numbers
        """
    ).bindparams(bindparam("room_numbers", expanding=True))

    with get_db_connection() as conn:
        conn.execute(hotel_total_sql)
        conn.execute(
            hotel_upsert_sql,
            {
                "property_code": "DRE001",
                "name": "Dream Big Hotel",
                "total_rooms": 120,
            },
        )
        hotel_id = conn.execute(
            hotel_id_sql,
            {"property_code": "DRE001"},
        ).scalar_one()
        conn.execute(create_sql)
        conn.execute(index_sql)
        room_rows = build_rooms(int(hotel_id))
        conn.execute(upsert_sql, room_rows)
        conn.execute(
            prune_sql,
            {
                "property_code": "DRE001",
                "room_numbers": tuple(row["room_number"] for row in room_rows),
            },
        )
        total = conn.execute(
            count_sql,
            {"property_code": "DRE001"},
        ).scalar_one()
        conn.commit()

    print(f"[SEED] DRE001 rooms configured: {total}")
    if int(total) != 120:
        print("[SEED] Note: existing extra DRE001 room records were preserved.")


if __name__ == "__main__":
    main()
