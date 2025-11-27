# guzo_backend/api/frontdesk_assign_api.py
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from guzo_db.postgres_hotels import assign_room_to_booking  # adjust import if needed

router = APIRouter(prefix="/frontdesk", tags=["Front Desk"])

AUTH_TOKEN = "admin-secret-123"


class AssignRoomPayload(BaseModel):
  booking_id: int
  room: str


@router.post("/assign-room")
async def assign_room(
  payload: AssignRoomPayload,
  authorization: Optional[str] = Header(None),
):
  # Simple header auth – same as your other endpoints
  if authorization != f"Bearer {AUTH_TOKEN}":
    raise HTTPException(status_code=401, detail="Unauthorized")

  try:
    updated = assign_room_to_booking(
      booking_id=payload.booking_id,
      room_number=payload.room,
    )
  except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to assign room: {e}")

  return updated
