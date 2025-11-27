from typing import Dict, Any, List
from sqlalchemy.orm import Session

def build_daily_report(db: Session, business_date):

    # --- Arrivals ---
    arrivals = db.execute("""
        SELECT * FROM bookings 
        WHERE check_in_date = :d 
        AND booking_status IN ('confirmed','reserved','guaranteed')
    """, {"d": business_date}).fetchall()

    # --- In House ---
    in_house = db.execute("""
        SELECT * FROM bookings
        WHERE booking_status = 'in_house'
        AND check_in_date <= :d
        AND check_out_date >= :d
    """, {"d": business_date}).fetchall()

    # --- Departures ---
    departures = db.execute("""
        SELECT * FROM bookings 
        WHERE check_out_date = :d
        AND booking_status IN ('in_house','checked_out')
    """, {"d": business_date}).fetchall()

    # --- Occupancy ---
    total_rooms = 2  # TODO load from rooms table
    rooms_sold = len(in_house)
    occupancy = (rooms_sold / total_rooms * 100) if total_rooms else 0

    return {
        "business_date": str(business_date),
        "arrivals": [dict(a) for a in arrivals],
        "in_house": [dict(i) for i in in_house],
        "departures": [dict(d) for d in departures],
        "occupancy_summary": {
            "total_rooms": total_rooms,
            "rooms_sold": rooms_sold,
            "occupied_pct": round(occupancy, 2)
        }
    }
