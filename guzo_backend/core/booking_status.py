# guzo_backend/core/booking_status.py

from enum import Enum


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    IN_HOUSE = "in_house"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


ACTIVE_STATUSES = (
    BookingStatus.CONFIRMED.value,
    BookingStatus.IN_HOUSE.value,
)
