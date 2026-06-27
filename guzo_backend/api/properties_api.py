from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.property_service import list_properties
from guzo_backend.services.pms_security_service import accessible_property_codes


router = APIRouter(tags=["properties"])


@router.get("/properties")
def get_properties(
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    allowed_codes = accessible_property_codes(db, user_email=x_pms_user_email)
    properties = list_properties(db)
    if allowed_codes is not None:
        properties = [row for row in properties if row.get("code") in allowed_codes]
    db.commit()
    return {"properties": properties}
