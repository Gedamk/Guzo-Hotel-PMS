# guzo_backend/db/postgres_rooms.py

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from contextlib import closing

from ..core.postgres_db import get_db_connection


# ---------------------------------------------------------------------------
# 0. Compatibility helper for older code (availability router, etc.)
# ---------------------------------------------------------------------------

def get_connection():
    """
    Backwards-compatible helper so older modules that import
    `from ..db.postgres_rooms import get_connection`
    still work.

    Internally this just calls core.postgres_db.get_db_connection().
    """
    return get_db_connection()


# ---------------------------------------------------------------------------
# 1. Rooms summary for occupancy / house count
# ---------------------------------------------------------------------------

def get_rooms_summary_by_property() -> Dict[str, Dict[str, int]]:
    """
    Return aggregated room counts per property from the `rooms` table.

    SAFE VERSION:
      - Only requires: rooms(property_code, ...)
      - Does NOT assume `status` or `is_out_of_order` columns exist.
      - Sets out_of_order_rooms = 0 for now.
    """
    conn = get_db_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT
                    property_code,
                    COUNT(*) AS total_rooms
                FROM rooms
                GROUP BY property_code
                ORDER BY property_code
                """
            )
            rows = cur.fetchall()

        summary: Dict[str, Dict[str, int]] = {}
        for property_code, total_rooms in rows:
            summary[property_code] = {
                "total_rooms": int(total_rooms or 0),
                "out_of_order_rooms": 0,  # placeholder until schema includes OOO
            }
        return summary
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Generic "list rooms" helper (used by dashboard / API)
# ---------------------------------------------------------------------------

def get_all_rooms(
    property_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return a list of rooms.

    If property_code is given, only rooms for that property are returned.
    Otherwise, rooms for all properties are returned.
    """
    conn = get_db_connection()
    try:
        with closing(conn.cursor()) as cur:
            if property_code:
                cur.execute(
                    """
                    SELECT
                        id,
                        property_code,
                        room_number,
                        room_type,
                        status,
                        COALESCE(is_out_of_order, FALSE) AS is_out_of_order
                    FROM rooms
                    WHERE property_code = %s
                    ORDER BY room_number
                    """,
                    (property_code,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        id,
                        property_code,
                        room_number,
                        room_type,
                        status,
                        COALESCE(is_out_of_order, FALSE) AS is_out_of_order
                    FROM rooms
                    ORDER BY property_code, room_number
                    """
                )
            rows = cur.fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            (
                rid,
                pcode,
                room_number,
                room_type,
                status,
                is_out_of_order,
            ) = row
            result.append(
                {
                    "id": rid,
                    "property_code": pcode,
                    "room_number": room_number,
                    "room_type": room_type,
                    "status": status,
                    "is_out_of_order": bool(is_out_of_order),
                }
            )
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. Internal helpers for argument parsing (backwards compatible)
# ---------------------------------------------------------------------------

def _parse_assign_room_args(
    *args,
    **kwargs,
) -> Tuple[int, str, str]:
    """
    Helper to keep backward compatibility with older calls that might use
    positional args or keyword args.

    Expected logical parameters:
      - booking_id: int
      - property_code: str
      - room_number: str
    """
    booking_id = kwargs.get("booking_id")
    property_code = kwargs.get("property_code")
    room_number = kwargs.get("room_number")

    # Fallbacks for positional args: (booking_id, property_code, room_number)
    if booking_id is None and len(args) > 0:
        booking_id = args[0]
    if property_code is None and len(args) > 1:
        property_code = args[1]
    if room_number is None and len(args) > 2:
        room_number = args[2]

    if booking_id is None or property_code is None or room_number is None:
        raise ValueError(
            "assign_room_to_booking requires booking_id, property_code, and room_number"
        )

    return int(booking_id), str(property_code), str(room_number)


def _parse_status_transition_args(
    *args,
    **kwargs,
) -> Tuple[int, str]:
    """
    Helper for apply_booking_status_transition, also backward compatible.

    Expected logical parameters:
      - booking_id: int
      - new_status: str
    """
    booking_id = kwargs.get("booking_id")
    new_status = kwargs.get("new_status")

    if booking_id is None and len(args) > 0:
        booking_id = args[0]
    if new_status is None and len(args) > 1:
        new_status = args[1]

    if booking_id is None or new_status is None:
        raise ValueError(
            "apply_booking_status_transition requires booking_id and new_status"
        )

    return int(booking_id), str(new_status)


# ---------------------------------------------------------------------------
# 4. Booking / room assignment
# ---------------------------------------------------------------------------

def assign_room_to_booking(*args, **kwargs) -> None:
    """
    Assign a room to a booking and keep room status consistent.
    """
    booking_id, property_code, room_number = _parse_assign_room_args(
        *args, **kwargs
    )

    conn = get_db_connection()
    try:
        with closing(conn.cursor()) as cur:
            # 1. Find existing room for this booking (if any)
            cur.execute(
                """
                SELECT property_code, room_number
                FROM bookings
                WHERE id = %s
                """,
                (booking_id,),
            )
            row = cur.fetchone()
            old_property_code: Optional[str] = None
            old_room_number: Optional[str] = None
            if row:
                old_property_code, old_room_number = row

            # 2. Update booking to new property/room
            cur.execute(
                """
                UPDATE bookings
                SET property_code = %s,
                    room_number = %s
                WHERE id = %s
                """,
                (property_code, room_number, booking_id),
            )

            # 3. Free old room if it's different
            if old_property_code and old_room_number:
                if (
                    old_property_code != property_code
                    or old_room_number != room_number
                ):
                    cur.execute(
                        """
                        UPDATE rooms
                        SET status = 'available'
                        WHERE property_code = %s
                          AND room_number = %s
                        """,
                        (old_property_code, old_room_number),
                    )

            # 4. Mark new room as occupied
            cur.execute(
                """
                UPDATE rooms
                SET status = 'occupied'
                WHERE property_code = %s
                  AND room_number = %s
                """,
                (property_code, room_number),
            )

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Booking status transitions
# ---------------------------------------------------------------------------

def apply_booking_status_transition(*args, **kwargs) -> None:
    """
    Apply a status transition to a booking and keep the associated room
    occupancy in sync.
    """
    booking_id, new_status = _parse_status_transition_args(*args, **kwargs)
    new_status = new_status.strip().lower()

    conn = get_db_connection()
    try:
        with closing(conn.cursor()) as cur:
            # 1. Get current booking room information
            cur.execute(
                """
                SELECT property_code, room_number
                FROM bookings
                WHERE id = %s
                """,
                (booking_id,),
            )
            row = cur.fetchone()
            if not row:
                return

            property_code, room_number = row

            # 2. Update booking status
            cur.execute(
                """
                UPDATE bookings
                SET status = %s
                WHERE id = %s
                """,
                (new_status, booking_id),
            )

            # 3. Adjust room status based on new booking status
            if property_code and room_number:
                if new_status == "in_house":
                    cur.execute(
                        """
                        UPDATE rooms
                        SET status = 'occupied'
                        WHERE property_code = %s
                          AND room_number = %s
                        """,
                        (property_code, room_number),
                    )
                elif new_status in ("checked_out", "cancelled"):
                    cur.execute(
                        """
                        UPDATE rooms
                        SET status = 'available'
                        WHERE property_code = %s
                          AND room_number = %s
                        """,
                        (property_code, room_number),
                    )
                # for 'confirmed' we leave room status unchanged

        conn.commit()
    finally:
        conn.close()
