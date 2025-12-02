# guzo_backend/api/rooms_api.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_simple_token  # same simple auth used elsewhere
from ..db.postgres_rooms import get_rooms_summary_by_property, get_all_rooms

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
    dependencies=[Depends(verify_simple_token)],
)


@router.get("/summary")
def rooms_summary():
    """
    Return per-property room totals for occupancy and house count.

    Response shape:

    {
      "DRE001": {
        "total_rooms": 60,
        "out_of_order_rooms": 2
      },
      "N&N002": {
        "total_rooms": 45,
        "out_of_order_rooms": 1
      }
    }
    """
    summary = get_rooms_summary_by_property()
    if not summary:
        # Not an error technically, but helps debugging on empty DB.
        return {}
    return summary


@router.get("")
def list_rooms(property_code: str | None = None):
    """
    Optional helper: list rooms. Useful later for housekeeping screens.
    """
    return get_all_rooms(property_code=property_code)
