# guzo_backend/core/availability_engine.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from guzo_backend.db.postgres_bookings import get_connection
from guzo_backend.core.booking_status import ACTIVE_STATUSES
from typing import Any, Dict
from typing import Any, Dict, List



@dataclass
class DailyAvailability:
    property_code: str
    date: date
    rooms_total: int
    rooms_occupied: int

    @property
    def rooms_available(self) -> int:
        return max(self.rooms_total - self.rooms_occupied, 0)

    @property
    def occupancy_pct(self) -> float:
        if self.rooms_total <= 0:
            return 0.0
        return (self.rooms_occupied / self.rooms_total) * 100.0


def _fetch_rooms_total(property_code: str) -> int:
    """
    Total sellable rooms for a property.
    """
    sql = """
        SELECT COUNT(*)
        FROM rooms
        WHERE property_code = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (property_code,))
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0


def _fetch_rooms_occupied_for_date(property_code: str, target: date) -> int:
    """
    Count room-nights occupied on a given date.

    Business logic:
    - booking overlaps the target date:
        check_in_date <= target < check_out_date
    - booking_status is 'confirmed' or 'in_house'
    """
    sql = f"""
        SELECT COUNT(*)
        FROM bookings
        WHERE property_code = %s
          AND check_in_date <= %s
          AND check_out_date > %s
          AND booking_status = ANY(%s)
    """
    statuses = list(ACTIVE_STATUSES)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (property_code, target, target, statuses))
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0


def compute_daily_availability(property_code: str, target: date) -> DailyAvailability:
    rooms_total = _fetch_rooms_total(property_code)
    rooms_occupied = _fetch_rooms_occupied_for_date(property_code, target)
    return DailyAvailability(
        property_code=property_code,
        date=target,
        rooms_total=rooms_total,
        rooms_occupied=rooms_occupied,
    )


def compute_availability_range(
    property_code: str,
    start: date,
    end: date,
) -> List[DailyAvailability]:
    """
    Inclusive range [start, end].
    """
    result: List[DailyAvailability] = []
    current = start
    while current <= end:
        result.append(compute_daily_availability(property_code, current))
        current += timedelta(days=1)
    return result

def daily_availability_to_dict(availability: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility helper.

    Older code imports `daily_availability_to_dict` from this module.
    Our engine functions now already return plain dicts, so this simply
    returns the input as-is.
    """
    # If availability is not already a dict (e.g. a Pydantic model),
    # you can adapt here later. For now we keep it simple.
    return dict(availability)

def list_availability_to_dicts(rows: List[Any]) -> List[Dict[str, Any]]:
    """
    Compatibility helper.

    Older code expects a function that converts a list of availability
    objects into plain dicts. Our engine may already give dicts or
    Pydantic models, so we handle both.
    """
    result: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            # already a dict
            result.append(row)
        elif hasattr(row, "model_dump"):
            # Pydantic v2 style
            result.append(row.model_dump())
        elif hasattr(row, "dict"):
            # Pydantic v1 style
            result.append(row.dict())
        else:
            # Last resort: try to cast to dict (e.g. from Row or namedtuple)
            result.append(dict(row))
    return result
