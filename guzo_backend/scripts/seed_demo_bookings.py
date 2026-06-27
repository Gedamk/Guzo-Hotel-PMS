# guzo_backend/scripts/seed_demo_bookings.py
"""
Seed hotel-standard PMS demo bookings.

Scenarios:
- Bekele Mola: 3-night five-star walk-in, already in-house with room assigned.
- Single guest: 4-night standard-room reservation from the website chatbot.
- Group booking: five guests confirmed from Telegram.

The insert is schema-aware because this project has multiple historical booking
table shapes. It writes rich PMS fields when columns exist and skips optional
columns when an older local database does not have them.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

from guzo_backend.dependencies import get_db


PROPERTY_CODE = "DRE001"
DEFAULT_RATE_ETB = 5200


def _load_hotel_id_map(db) -> dict[str, int]:
    rows = db.execute(text("SELECT id, property_code FROM hotels")).fetchall()
    return {row[1]: row[0] for row in rows}


def _load_booking_columns(db) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bookings'
            """
        )
    ).fetchall()
    return {row[0] for row in rows}


def _insert_booking(db, columns: set[str], row: dict[str, Any]) -> None:
    insertable = {key: value for key, value in row.items() if key in columns}
    column_sql = ", ".join(insertable.keys())
    value_sql = ", ".join(f":{key}" for key in insertable.keys())

    db.execute(
        text(
            f"""
            INSERT INTO bookings ({column_sql})
            VALUES ({value_sql})
            """
        ),
        insertable,
    )


def _booking_row(
    *,
    confirmation_id: str,
    hotel_id: int,
    property_code: str,
    guest_name: str,
    check_in_date: date,
    check_out_date: date,
    booking_status: str,
    source: str,
    channel: str,
    room_type: str,
    room_number: str | None,
    rate_per_night_etb: int,
    payment_status: str,
    payment_method: str | None,
    notes: str,
) -> dict[str, Any]:
    nights = max((check_out_date - check_in_date).days, 1)
    total_amount = rate_per_night_etb * nights

    return {
        "confirmation_id": confirmation_id,
        "hotel_id": hotel_id,
        "property_code": property_code,
        "guest_name": guest_name,
        "guest_email": f"{guest_name.lower().replace(' ', '.')}@example.com",
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "nights": nights,
        "room_type": room_type,
        "room_number": room_number,
        "rate_per_night_etb": rate_per_night_etb,
        "total_revenue_etb": total_amount,
        "total_amount_etb": total_amount,
        "total_amount": total_amount,
        "currency": "ETB",
        "booking_status": booking_status,
        "payment_status": payment_status,
        "payment_method": payment_method,
        "source": source,
        "channel": channel,
        "notes": notes,
    }


def seed_demo_bookings(business_date: date) -> None:
    db = next(get_db())
    hotel_id_by_prop = _load_hotel_id_map(db)
    if PROPERTY_CODE not in hotel_id_by_prop:
        raise RuntimeError(
            f"Expected hotel with property_code {PROPERTY_CODE} to exist in hotels."
        )

    hotel_id = hotel_id_by_prop[PROPERTY_CODE]
    columns = _load_booking_columns(db)

    db.execute(
        text(
            """
            DELETE FROM bookings
            WHERE confirmation_id LIKE 'GZ-DEMO-%'
               OR guest_name IN (
                   'Bekele Mola',
                   'Hanna Tesfaye',
                   'Mekdes Corporate Group - 5 Guests'
               )
            """
        )
    )

    scenarios = [
        _booking_row(
            confirmation_id="GZ-DEMO-WI-BEKELE-MOLA",
            hotel_id=hotel_id,
            property_code=PROPERTY_CODE,
            guest_name="Bekele Mola",
            check_in_date=business_date,
            check_out_date=business_date + timedelta(days=3),
            booking_status="in_house",
            source="Walk-In",
            channel="Front Desk",
            room_type="Deluxe King",
            room_number="501",
            rate_per_night_etb=DEFAULT_RATE_ETB,
            payment_status="deposit_received",
            payment_method="pos",
            notes=(
                "Five-star walk-in flow: ID verified, rate quoted, payment "
                "deposit captured, room 501 assigned, key issued, welcome "
                "amenity requested, folio open for checkout after 3 nights."
            ),
        ),
        _booking_row(
            confirmation_id="GZ-DEMO-WEB-SINGLE-4N",
            hotel_id=hotel_id,
            property_code=PROPERTY_CODE,
            guest_name="Hanna Tesfaye",
            check_in_date=business_date + timedelta(days=1),
            check_out_date=business_date + timedelta(days=5),
            booking_status="confirmed",
            source="Website Chatbot",
            channel="Website Chatbot",
            room_type="Standard Room",
            room_number=None,
            rate_per_night_etb=DEFAULT_RATE_ETB,
            payment_status="guaranteed",
            payment_method="card",
            notes=(
                "Single guest reservation standard: 4 nights, standard room, "
                "guaranteed booking, confirmation sent by website chatbot."
            ),
        ),
        _booking_row(
            confirmation_id="GZ-DEMO-TG-GROUP-5",
            hotel_id=hotel_id,
            property_code=PROPERTY_CODE,
            guest_name="Mekdes Corporate Group - 5 Guests",
            check_in_date=business_date + timedelta(days=2),
            check_out_date=business_date + timedelta(days=5),
            booking_status="confirmed",
            source="Telegram",
            channel="Telegram Bot",
            room_type="Standard Room x3",
            room_number=None,
            rate_per_night_etb=DEFAULT_RATE_ETB * 3,
            payment_status="guaranteed",
            payment_method="bank_transfer",
            notes=(
                "Group reservation standard: 5 guests, 3 standard rooms, "
                "Telegram intake, group profile noted, arrival list required, "
                "prepayment guarantee requested."
            ),
        ),
    ]

    for scenario in scenarios:
        _insert_booking(db, columns, scenario)

    db.commit()
    print("[SEED] Hotel-standard PMS scenarios inserted for:", business_date)


def main() -> None:
    seed_demo_bookings(date.today())


if __name__ == "__main__":
    main()
