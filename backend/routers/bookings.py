from fastapi import APIRouter, HTTPException
from backend.schemas.booking import BookingRequest, BookingResponse

router = APIRouter()

# In-memory DB for now
bookings_db = []

@router.post("/", response_model=BookingResponse)
def create_booking(booking: BookingRequest):
    new_booking = {
        "id": len(bookings_db) + 1,
        "guest_name": booking.guest_name,
        "room_type": booking.room_type,
        "check_in": booking.check_in,
        "check_out": booking.check_out,
        "status": "confirmed"
    }
    bookings_db.append(new_booking)
    return new_booking

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int):
    for b in bookings_db:
        if b["id"] == booking_id:
            return b
    raise HTTPException(status_code=404, detail="Booking not found")
