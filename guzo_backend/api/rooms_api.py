# guzo_backend/api/rooms_api.py

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from ..db.postgres_rooms import get_rooms_summary_by_property, get_all_rooms
from ..dependencies import get_db
from ..services.pms_security_service import require_property_access

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)


@router.get("/summary")
def rooms_summary(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
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
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    summary = get_rooms_summary_by_property()
    if not summary:
        # Not an error technically, but helps debugging on empty DB.
        return {}
    return {property_code: summary[property_code]} if property_code in summary else {}


@router.get("")
def list_rooms(
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Optional helper: list rooms. Useful later for housekeeping screens.
    """
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    return get_all_rooms(property_code=property_code)
