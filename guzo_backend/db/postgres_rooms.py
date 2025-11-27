# guzo_backend/db/postgres_rooms.py
#
# Central helpers for:
#  - Assigning rooms to bookings
#  - Keeping room.status in sync with booking_status
#
# Uses:
#   bookings(id, booking_status, hotel_id, property_code, ...)
#   rooms(id, hotel_id, property_code, room_number, status, booking_id, ...)

import os
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


def assign_room_to_booking(booking_id: int) -> Optional[str]:
    """
    Assign the first free room for this booking's hotel/property.

    Policy (simple, but safe for v1):
      - Find a room WHERE:
          * property_code OR hotel_id matches booking
          * booking_id IS NULL
          * status in ('available', 'vacant_clean')
      - Pick the smallest room_number
      - Set rooms.booking_id = booking_id
      - Set rooms.status = 'occupied'

    Returns:
      - room_number as string if assigned
      - None if no free room or booking not found
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Lock the booking row so we don't race with another front desk action
                cur.execute(
                    """
                    SELECT id, hotel_id, property_code
                    FROM bookings
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (booking_id,),
                )
                booking = cur.fetchone()
                if not booking:
                    logger.warning("assign_room_to_booking: booking %s not found", booking_id)
                    return None

                hotel_id = booking["hotel_id"]
                property_code = booking["property_code"]

                if not hotel_id and not property_code:
                    logger.warning(
                        "assign_room_to_booking: booking %s has no hotel_id/property_code",
                        booking_id,
                    )
                    return None

                # Choose free room by property_code if available, otherwise by hotel_id
                if property_code:
                    cur.execute(
                        """
                        SELECT id, room_number
                        FROM rooms
                        WHERE property_code = %s
                          AND booking_id IS NULL
                          AND status IN ('available', 'vacant_clean')
                        ORDER BY room_number
                        LIMIT 1
                        """,
                        (property_code,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, room_number
                        FROM rooms
                        WHERE hotel_id = %s
                          AND booking_id IS NULL
                          AND status IN ('available', 'vacant_clean')
                        ORDER BY room_number
                        LIMIT 1
                        """,
                        (hotel_id,),
                    )

                room = cur.fetchone()
                if not room:
                    logger.info(
                        "assign_room_to_booking: no free room for booking %s (property=%s, hotel_id=%s)",
                        booking_id,
                        property_code,
                        hotel_id,
                    )
                    return None

                cur.execute(
                    """
                    UPDATE rooms
                    SET booking_id = %s,
                        status = 'occupied',
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (booking_id, room["id"]),
                )

                logger.info(
                    "assign_room_to_booking: assigned room %s to booking %s",
                    room["room_number"],
                    booking_id,
                )

                return str(room["room_number"])
    except Exception:
        logger.exception("assign_room_to_booking: error for booking %s", booking_id)
        raise
    finally:
        conn.close()


def apply_booking_status_transition(booking_id: int, new_status: str) -> None:
    """
    Apply booking_status change AND update linked room.status accordingly.

    Room lifecycle (v1, Guzo standard):

      - new_status = 'in_house'
          booking.booking_status -> 'in_house'
          room.status           -> 'occupied'    (guest is in-house)

      - new_status = 'checked_out'
          booking.booking_status -> 'checked_out'
          room.status           -> 'vacant_dirty'
          room.booking_id       -> NULL         (ready for cleaning / next booking)

      - new_status in ('cancelled', 'no_show')
          booking.booking_status -> 'cancelled' / 'no_show'
          room.status           -> 'available'
          room.booking_id       -> NULL

      - otherwise:
          only update booking.booking_status (no room change)

    NOTE: We do NOT assume an 'updated_at' column on bookings, because
          your current schema sample didn't include it.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Lock booking
                cur.execute(
                    """
                    SELECT id, booking_status
                    FROM bookings
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (booking_id,),
                )
                booking = cur.fetchone()
                if not booking:
                    raise ValueError(f"Booking {booking_id} not found")

                # Lock any room linked to this booking
                cur.execute(
                    """
                    SELECT id, status
                    FROM rooms
                    WHERE booking_id = %s
                    FOR UPDATE
                    """,
                    (booking_id,),
                )
                room = cur.fetchone()

                # Update booking status
                cur.execute(
                    """
                    UPDATE bookings
                    SET booking_status = %s
                    WHERE id = %s
                    """,
                    (new_status, booking_id),
                )

                # Update room if one is linked
                if room:
                    room_id = room["id"]

                    if new_status == "in_house":
                        # Guest is now in-house; keep room occupied
                        cur.execute(
                            """
                            UPDATE rooms
                            SET status = 'occupied',
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (room_id,),
                        )

                    elif new_status == "checked_out":
                        # Guest left: mark room dirty and free it from this booking
                        cur.execute(
                            """
                            UPDATE rooms
                            SET status = 'vacant_dirty',
                                booking_id = NULL,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (room_id,),
                        )

                    elif new_status in ("cancelled", "no_show"):
                        # Booking won't stay: free the room
                        cur.execute(
                            """
                            UPDATE rooms
                            SET status = 'available',
                                booking_id = NULL,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (room_id,),
                        )

                    # For any other status (e.g. 'confirmed'), we leave the room as-is.

                logger.info(
                    "apply_booking_status_transition: booking %s -> %s",
                    booking_id,
                    new_status,
                )
    except Exception:
        logger.exception(
            "apply_booking_status_transition: error for booking %s -> %s",
            booking_id,
            new_status,
        )
        raise
    finally:
        conn.close()
