from typing import Dict, Any

def assign_room_to_booking(booking_id: int, room_number: str) -> Dict[str, Any]:
    """
    Update a booking with a room number and mark it as in_house.
    ⚠️ Adjust table/column names to match your real schema.
    """
    sql = """
        UPDATE bookings
        SET
            room_number = %s,
            status = 'in_house'
        WHERE id = %s
        RETURNING
            id,
            guest_name,
            hotel_name,
            property_code,
            room_number,
            check_in_date,
            check_out_date,
            nights,
            status,
            channel,
            total_amt,
            note;
    """

    # 🔹 IMPORTANT: this assumes you already have get_connection()
    # imported/defined earlier in this file, just like your other functions.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_number, booking_id))
            row = cur.fetchone()

    if not row:
        raise ValueError(f"Booking {booking_id} not found")

    return {
        "id": row[0],
        "guest_name": row[1],
        "hotel_name": row[2],
        "property_code": row[3],
        "room": row[4],
        "check_in_date": row[5],
        "check_out_date": row[6],
        "nights": row[7],
        "status": row[8],
        "channel": row[9],
        "total_amt": row[10],
        "note": row[11],
    }
