# guzo_backend/routers/bot_availability.py
#
# Lightweight wrapper for Telegram / bot clients.
# Delegates core logic to guzo_backend.routers.availability.search_availability
# and returns a simple JSON payload.

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from guzo_backend.routers.availability import (
    search_availability as core_search_availability,
)

router = APIRouter(prefix="/bot", tags=["bot-availability"])


class BotAvailabilityResponse(BaseModel):
    property_code: str
    check_in: str
    check_out: str
    requested_rooms: int
    total_rooms: int
    overlapping_bookings: int
    available_rooms: int
    available: bool
    message: str


@router.get("/availability", response_model=BotAvailabilityResponse)
def bot_availability(
    property_code: str = Query(..., min_length=1),
    check_in: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    check_out: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    rooms: int = Query(1, ge=1),
):
    """
    Wrapper endpoint used by Telegram bot (backend_client.check_availability_for_bot).

    It calls the core /availability/search logic and repackages the response
    into a simpler JSON tailored for bots.
    """

    core = core_search_availability(
        property_code=property_code,
        check_in=check_in,
        check_out=check_out,
        rooms=rooms,
    )

    if core.is_available:
        msg = (
            f"Yes, {core.available_rooms} room(s) available at "
            f"{core.property_code} from {core.check_in} to {core.check_out}."
        )
    else:
        msg = (
            f"Sorry, only {core.available_rooms} room(s) available at "
            f"{core.property_code} from {core.check_in} to {core.check_out}."
        )

    return BotAvailabilityResponse(
        property_code=core.property_code,
        check_in=core.check_in,
        check_out=core.check_out,
        requested_rooms=core.rooms_requested,
        total_rooms=core.total_rooms,
        overlapping_bookings=core.overlapping_bookings,
        available_rooms=core.available_rooms,
        available=core.is_available,
        message=msg,
    )
