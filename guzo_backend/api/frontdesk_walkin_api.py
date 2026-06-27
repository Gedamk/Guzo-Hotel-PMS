# guzo_backend/api/frontdesk_walkin_api.py

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..services.audit_log_service import record_audit_log
from ..services.pms_security_service import record_pms_audit_log, require_pms_permission

router = APIRouter(prefix="/frontdesk", tags=["frontdesk-walkin"])


class WalkInBookingCreate(BaseModel):
    """
    Payload expected from the Front Desk Walk-In form.
    This should line up with what the React WalkInBookingModal sends.
    """

    property_code: str = Field(..., description="Hotel property code, e.g. DRE001")
    room_number: Optional[str] = Field(
        None,
        description="Assigned room number (e.g. 200). If omitted, stays as TBD.",
    )
    room_type: Optional[str] = Field(
        None,
        description="Room type code/name (optional – for future use).",
    )
    guest_name: str
    adults: Optional[int] = None
    children: Optional[int] = None
    is_vip: bool = False
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    purpose_of_visit: Optional[str] = None
    check_in_date: date
    check_out_date: date
    currency: str = "ETB"
    rate_per_night_etb: Optional[float] = None
    total_amount_etb: Optional[float] = None
    discount_amount: Optional[float] = None
    extra_bed_charge: Optional[float] = None
    tax_percent: Optional[float] = None
    tax_amount: Optional[float] = None
    service_charge_percent: Optional[float] = None
    service_charge_amount: Optional[float] = None
    vat_percent: Optional[float] = None
    vat_amount: Optional[float] = None
    downpayment_amount: Optional[float] = None
    payment_method: Optional[str] = None
    amount_paid_now_etb: Optional[float] = None
    notes: Optional[str] = None

    @validator("check_out_date")
    def validate_dates(cls, v, values):
        check_in = values.get("check_in_date")
        if check_in and v < check_in:
            raise ValueError("check_out_date must be on or after check_in_date")
        return v


def _generate_confirmation_id(property_code: str) -> str:
    """
    Simple confirmation ID generator for walk-ins.
    Example: GZ-WI-DRE001-251202094530
    """
    ts = datetime.now().strftime("%y%m%d%H%M%S")
    return f"GZ-WI-{property_code}-{ts}"


def _get_hotel_id(db: Session, property_code: str) -> int:
    row = db.execute(
        text(
            """
            SELECT id
            FROM hotels
            WHERE property_code = :property_code
            LIMIT 1
            """
        ),
        {"property_code": property_code},
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hotel found for property_code={property_code}",
        )

    return int(row[0])


def _money(value: Optional[float]) -> float:
    return float(value or 0)


def _ensure_booking_currency_column(db: Session) -> None:
    db.execute(
        text(
            """
            ALTER TABLE bookings
            ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ETB'
            """
        )
    )


def _build_walkin_notes(payload: WalkInBookingCreate, total_amount: float) -> str:
    lines = []
    if payload.notes:
        lines.append(payload.notes.strip())

    profile_parts = [
        f"Adults: {payload.adults}" if payload.adults is not None else None,
        f"Children: {payload.children}" if payload.children is not None else None,
        "VIP: Yes" if payload.is_vip else "VIP: No",
        f"Room Type: {payload.room_type}" if payload.room_type else None,
        f"Document: {payload.document_type or 'ID'} {payload.document_number}"
        if payload.document_number
        else None,
        f"Email: {payload.email}" if payload.email else None,
        f"Phone: {payload.phone}" if payload.phone else None,
        f"Purpose: {payload.purpose_of_visit}" if payload.purpose_of_visit else None,
    ]
    receipt_parts = [
        f"Currency: {payload.currency.upper()}",
        f"Rate/Night: {_money(payload.rate_per_night_etb):.2f}",
        f"Discount: {_money(payload.discount_amount):.2f}",
        f"Extra Bed Charge: {_money(payload.extra_bed_charge):.2f}",
        f"Tax: {_money(payload.tax_amount):.2f} ({_money(payload.tax_percent):.2f}%)",
        f"Service Charge: {_money(payload.service_charge_amount):.2f} ({_money(payload.service_charge_percent):.2f}%)",
        f"VAT: {_money(payload.vat_amount):.2f} ({_money(payload.vat_percent):.2f}%)",
        f"Downpayment: {_money(payload.downpayment_amount):.2f}",
        f"Amount Paid Now: {_money(payload.amount_paid_now_etb):.2f}",
        f"Total: {total_amount:.2f}",
        f"Payment Method: {payload.payment_method}" if payload.payment_method else None,
    ]

    lines.append(
        "Guest Profile | "
        + " | ".join(part for part in profile_parts if part is not None)
    )
    lines.append(
        "Receipt Prep | "
        + " | ".join(part for part in receipt_parts if part is not None)
    )
    return "\n".join(lines)


@router.post("/walkin", status_code=status.HTTP_201_CREATED)
def create_walkin_booking(
    payload: WalkInBookingCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    """
    Create a new walk-in booking from the Front Desk console.

    Design:
    - Insert into `bookings` table using the same core fields
      that the Front Desk and Housekeeping flows expect:
        * confirmation_id
        * guest_name
        * property_code
        * room_number (optional)
        * check_in_date
        * check_out_date
        * booking_status
        * channel
        * total_amount
        * notes

    - For now we treat walk-ins as already at the desk and checked in:
        booking_status = 'in_house'
        channel        = 'Walk-In'

    - The Front Desk UI will refresh via /frontdesk/bookings after success.
    """

    # Compute nights & total if not explicitly provided
    nights = (payload.check_out_date - payload.check_in_date).days or 1
    room_subtotal = (
        payload.rate_per_night_etb * nights
        if payload.rate_per_night_etb is not None
        else 0
    )
    total_amount = payload.total_amount_etb
    if total_amount is None:
        total_amount = (
            room_subtotal
            - _money(payload.discount_amount)
            + _money(payload.extra_bed_charge)
            + _money(payload.tax_amount)
            + _money(payload.service_charge_amount)
            + _money(payload.vat_amount)
        )
    total_amount = max(float(total_amount or 0), 0)
    notes = _build_walkin_notes(payload, total_amount)

    property_code = payload.property_code.strip().upper()
    actor = require_pms_permission(
        db,
        permission_key="frontdesk.check_in",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    confirmation_id = _generate_confirmation_id(property_code)
    hotel_id = _get_hotel_id(db, property_code)

    try:
        _ensure_booking_currency_column(db)
        insert_sql = text(
            """
            INSERT INTO bookings (
                confirmation_id,
                hotel_id,
                guest_name,
                property_code,
                room_number,
                check_in_date,
                check_out_date,
                booking_status,
                channel,
                currency,
                total_amount,
                notes
            )
            VALUES (
                :confirmation_id,
                :hotel_id,
                :guest_name,
                :property_code,
                :room_number,
                :check_in_date,
                :check_out_date,
                :booking_status,
                :channel,
                :currency,
                :total_amount,
                :notes
            )
            RETURNING id
            """
        )

        result = db.execute(
            insert_sql,
            {
                "confirmation_id": confirmation_id,
                "hotel_id": hotel_id,
                "guest_name": payload.guest_name.strip(),
                "property_code": property_code,
                "room_number": payload.room_number,
                "check_in_date": payload.check_in_date,
                "check_out_date": payload.check_out_date,
                # Guest is created as in-house for walk-in
                "booking_status": "in_house",
                "channel": "Walk-In",
                "currency": payload.currency.upper(),
                "total_amount": total_amount,
                "notes": notes,
            },
        )
        new_id_row = result.fetchone()
        new_booking_id = int(new_id_row[0]) if new_id_row else None
        record_audit_log(
            db,
            action="walk_in_created",
            entity_type="booking",
            entity_id=new_booking_id,
            hotel_id=hotel_id,
            property_code=property_code,
            business_date=payload.check_in_date,
            details={
                "guest_name": payload.guest_name.strip(),
                "room_number": payload.room_number,
                "room_type": payload.room_type,
                "adults": payload.adults,
                "children": payload.children,
                "is_vip": payload.is_vip,
                "document_type": payload.document_type,
                "email": payload.email,
                "phone": payload.phone,
                "purpose_of_visit": payload.purpose_of_visit,
                "currency": payload.currency.upper(),
                "discount_amount": payload.discount_amount,
                "extra_bed_charge": payload.extra_bed_charge,
                "tax_percent": payload.tax_percent,
                "tax_amount": payload.tax_amount,
                "service_charge_percent": payload.service_charge_percent,
                "service_charge_amount": payload.service_charge_amount,
                "vat_percent": payload.vat_percent,
                "vat_amount": payload.vat_amount,
                "downpayment_amount": payload.downpayment_amount,
                "payment_method": payload.payment_method,
                "amount_paid_now_etb": payload.amount_paid_now_etb,
                "total_amount": total_amount,
            },
        )
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor["email"],
            module="frontdesk",
            action="walk_in_checked_in",
            record_type="booking",
            record_id=new_booking_id,
            new_value={
                "guest_name": payload.guest_name.strip(),
                "confirmation_id": confirmation_id,
                "room_number": payload.room_number,
                "check_in_date": payload.check_in_date.isoformat(),
                "check_out_date": payload.check_out_date.isoformat(),
                "payment_method": payload.payment_method,
                "amount_paid_now_etb": payload.amount_paid_now_etb,
                "total_amount": total_amount,
            },
        )
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # Drives the "Failed to create walk-in booking" error message in the UI
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating walk-in booking: {exc}",
        ) from exc

    # Frontend only needs to know it succeeded; it will re-fetch bookings.
    return {"ok": True, "booking_id": new_booking_id}
