# guzo_backend/core/availability_messages.py

from __future__ import annotations

from datetime import date
from typing import Optional

from guzo_backend.core.availability_engine import compute_daily_availability


def format_daily_availability_message(
    property_code: str,
    as_of: Optional[date] = None,
    hotel_name: Optional[str] = None,
) -> str:
    """
    Build a human-readable message for bots / SMS / email.
    Example output:

    "Today (2025-11-25), Dream Big Hotel (DRE001) has:
     • 2 rooms total
     • 0 occupied
     • 2 available
     → Occupancy: 0.0%"

    If as_of is None, uses today's date.
    """
    if as_of is None:
        as_of = date.today()

    av = compute_daily_availability(property_code, as_of)
    display_name = hotel_name or property_code

    lines = [
        f"Today ({av.date}), {display_name} ({av.property_code}) has:",
        f" • {av.rooms_total} rooms total",
        f" • {av.rooms_occupied} occupied",
        f" • {av.rooms_available} available",
        f" → Occupancy: {av.occupancy_pct:.1f}%",
    ]
    return "\n".join(lines)
