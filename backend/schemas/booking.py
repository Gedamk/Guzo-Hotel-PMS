from pydantic import BaseModel
from datetime import date

class BookingRequest(BaseModel):
    guest_name: str
    room_type: str
    check_in: date
    check_out: date

class BookingResponse(BookingRequest):
    id: int
    status: str
