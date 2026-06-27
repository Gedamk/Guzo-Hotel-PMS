from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.rate_quote_service import RATE_PLANS, quote_stay

router = APIRouter(prefix="/rate-quote", tags=["rate-quote"])


class RateQuoteOut(BaseModel):
    property_code: str
    currency: str
    room_type: str
    rate_code: str
    rate_label: str
    nights: int
    rooms: int
    adults: int
    children: int
    base_rate_etb: float
    nightly_rate_etb: float
    room_subtotal_etb: float
    weekend_nights: int
    weekend_surcharge_etb: float
    extra_adult_count: int
    extra_child_count: int
    extra_guest_charge_etb: float
    service_charge_percent: float
    service_charge_etb: float
    tax_percent: float
    tax_etb: float
    net_revenue_etb: float
    gross_revenue_etb: float
    total_etb: float
    deposit_percent: float
    deposit_required_etb: float
    guarantee_required: bool
    cancellation_policy: str
    applied_rules: list[str]
    quote_notes: list[str]


@router.get("/quote", response_model=RateQuoteOut)
def get_rate_quote(
    property_code: str = Query(..., min_length=1, max_length=20),
    check_in: date = Query(...),
    check_out: date = Query(...),
    room_type: str | None = Query(None, max_length=100),
    rooms: int = Query(1, ge=1),
    adults: int = Query(1, ge=1),
    children: int = Query(0, ge=0),
    rate_code: str = Query("BAR", min_length=1, max_length=20),
    db: Session = Depends(get_db),
):
    try:
        return quote_stay(
            property_code=property_code,
            check_in=check_in,
            check_out=check_out,
            room_type=room_type,
            rooms=rooms,
            adults=adults,
            children=children,
            rate_code=rate_code,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/plans")
def list_rate_plans():
    return {
        "currency": "ETB",
        "plans": [
            {
                "code": code,
                "label": plan["label"],
                "deposit_percent": plan["deposit_percent"],
                "guarantee_required": plan["guarantee_required"],
                "cancellation_policy": plan["policy"],
            }
            for code, plan in RATE_PLANS.items()
        ],
    }
