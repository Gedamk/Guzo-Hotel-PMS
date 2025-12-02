# guzo_backend/scripts/seed_demo_bookings.py
"""
Seed demo bookings data for the portfolio console.

Aligned with current DB schema:
- bookings requires hotel_id (NOT NULL)
- we also use:
  property_code, guest_name, room_number,
  check_in_date, check_out_date, booking_status
"""

from datetime import date, timedelta

from sqlalchemy import text

from guzo_backend.dependencies import get_db


def _load_hotel_id_map(db) -> dict:
    """
    Load mapping: property_code -> hotel_id from hotels table.
    """
    rows = db.execute(text("SELECT id, property_code FROM hotels")).fetchall()
    mapping = {}
    for row in rows:
        # row[0] = id, row[1] = property_code
        hotel_id = row[0]
        prop_code = row[1]
        mapping[prop_code] = hotel_id
    return mapping


def seed_demo_bookings(business_date: date) -> None:
    """
    Create some sample bookings around the given business_date.
    """
    db = next(get_db())  # SQLAlchemy Session

    # Map property_code -> hotel_id
    hotel_id_by_prop = _load_hotel_id_map(db)
    if "DRE001" not in hotel_id_by_prop or "N&N002" not in hotel_id_by_prop:
        raise RuntimeError(
            "Expected hotels with property_code DRE001 and N&N002 to exist "
            "in the hotels table."
        )

    # 1) Clear previous demo rows by guest_name prefix
    db.execute(
        text("DELETE FROM bookings WHERE guest_name LIKE :prefix"),
        {"prefix": "Demo %"},
    )

    # 2) Define a few sample rows
    d0 = business_date
    d_minus1 = business_date - timedelta(days=1)
    d_plus1 = business_date + timedelta(days=1)
    d_plus3 = business_date + timedelta(days=3)

    demo_rows = [
        # In-house at Dream Big (came yesterday, leaves tomorrow)
        {
            "property_code": "DRE001",
            "guest_name": "Demo In-House Guest",
            "room_number": "200",
            "check_in_date": d_minus1,
            "check_out_date": d_plus1,
            "booking_status": "in_house",
        },
        # Departure today at Dream Big
        {
            "property_code": "DRE001",
            "guest_name": "Demo Departure Guest",
            "room_number": "201",
            "check_in_date": d_minus1 - timedelta(days=2),
            "check_out_date": d0,
            "booking_status": "departed",
        },
        # Arrival today at N&N Luxury
        {
            "property_code": "N&N002",
            "guest_name": "Demo Arrival Guest",
            "room_number": "305",
            "check_in_date": d0,
            "check_out_date": d_plus3,
            "booking_status": "confirmed",
        },
        # Future booking at N&N Luxury
        {
            "property_code": "N&N002",
            "guest_name": "Demo Future Booking",
            "room_number": None,
            "check_in_date": d_plus3,
            "check_out_date": d_plus3 + timedelta(days=2),
            "booking_status": "confirmed",
        },
    ]

    insert_sql = text(
        """
        INSERT INTO bookings (
            hotel_id,
            property_code,
            guest_name,
            room_number,
            check_in_date,
            check_out_date,
            booking_status
        )
        VALUES (
            :hotel_id,
            :property_code,
            :guest_name,
            :room_number,
            :check_in_date,
            :check_out_date,
            :booking_status
        )
        """
    )

    for row in demo_rows:
        prop_code = row["property_code"]
        hotel_id = hotel_id_by_prop.get(prop_code)
        if hotel_id is None:
            raise RuntimeError(f"No hotel_id found for property_code={prop_code}")

        db.execute(
            insert_sql,
            {
                "hotel_id": hotel_id,
                "property_code": prop_code,
                "guest_name": row["guest_name"],
                "room_number": row["room_number"],
                "check_in_date": row["check_in_date"],
                "check_out_date": row["check_out_date"],
                "booking_status": row["booking_status"],
            },
        )

    db.commit()
    print("[SEED] Demo bookings inserted for business date:", business_date)


def main() -> None:
    # Use your current demo business date
    business_date = date(2025, 12, 2)
    seed_demo_bookings(business_date)


if __name__ == "__main__":
    main()
