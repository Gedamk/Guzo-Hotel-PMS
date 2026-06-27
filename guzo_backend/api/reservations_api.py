from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.audit_log_service import record_audit_log
from guzo_backend.services.guest_profile_service import (
    find_or_create_guest_profile,
    link_guest_profile_to_booking,
    queue_guest_notification,
    queue_manager_alert,
    queue_prearrival_deposit_alert_if_needed,
)
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission
from guzo_backend.services.rate_quote_service import quote_stay
from guzo_backend.services.reservation_inventory_service import (
    cancel_waitlist as persist_cancel_waitlist,
    create_block as persist_create_block,
    create_waitlist as persist_create_waitlist,
    get_block,
    get_waitlist,
    list_blocks,
    list_waitlist,
    mark_waitlist_converted,
    review_waitlist as persist_review_waitlist,
    update_block as persist_update_block,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])

ACTIVE_STATUSES = {
    "confirmed",
    "reserved",
    "pending",
    "pending_guarantee",
    "in_house",
    "checked_in",
}

UNSELLABLE_ROOM_STATUSES = {
    "out_of_order",
    "out of order",
    "ooo",
    "out_of_service",
    "out of service",
    "oos",
    "maintenance",
}


class ReservationAvailabilityRequest(BaseModel):
    property_code: str = Field(..., min_length=1)
    check_in_date: date
    check_out_date: date
    room_type: str = Field("Standard Room", min_length=1)
    rooms: int = Field(1, ge=1)
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    rate_code: str = Field("BAR", min_length=1)

    @field_validator("property_code")
    @classmethod
    def normalize_property_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("rate_code")
    @classmethod
    def normalize_rate_code(cls, value: str) -> str:
        return value.strip().upper()


class ReservationCreateRequest(ReservationAvailabilityRequest):
    guest_name: str = Field(..., min_length=1)
    guest_email: str | None = None
    guest_phone: str | None = None
    reservation_type: str = Field("individual", min_length=1)
    source: str = Field("direct", min_length=1)
    company_name: str | None = None
    travel_agent_name: str | None = None
    event_name: str | None = None
    guarantee_type: str = Field("deposit_required", min_length=1)
    deposit_required: bool = True
    cancellation_policy: str | None = None
    special_requests: str | None = None
    vip_notes: str | None = None
    notes: str | None = None

    @field_validator("guest_name")
    @classmethod
    def normalize_guest_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("guest_name is required")
        return value


class ReservationUpdateRequest(BaseModel):
    property_code: str = Field(..., min_length=1)
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    room_type: str | None = None
    rate_code: str | None = None
    guarantee_type: str | None = None
    special_requests: str | None = None
    vip_notes: str | None = None
    notes: str | None = None

    @field_validator("property_code")
    @classmethod
    def normalize_property_code(cls, value: str) -> str:
        return value.strip().upper()


class ReservationCancelRequest(BaseModel):
    property_code: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=3)

    @field_validator("property_code")
    @classmethod
    def normalize_property_code(cls, value: str) -> str:
        return value.strip().upper()


class PropertyScopedRequest(BaseModel):
    property_code: str = Field(..., min_length=1)

    @field_validator("property_code")
    @classmethod
    def normalize_property_code(cls, value: str) -> str:
        return value.strip().upper()


class WaitlistCreateRequest(ReservationAvailabilityRequest):
    guest_name: str = Field(..., min_length=1)
    guest_email: str | None = None
    guest_phone: str | None = None
    source: str = Field("direct", min_length=1)
    notes: str | None = None


class WaitlistCancelRequest(PropertyScopedRequest):
    reason: str = Field(..., min_length=3)


class BlockCreateRequest(PropertyScopedRequest):
    block_name: str = Field(..., min_length=1)
    company_name: str | None = None
    contact_name: str = Field(..., min_length=1)
    contact_email: str | None = None
    contact_phone: str | None = None
    check_in_date: date
    check_out_date: date
    room_type: str = Field("Standard Room", min_length=1)
    rooms: int = Field(1, ge=1)
    rate_code: str = Field("GRP10", min_length=1)
    notes: str | None = None

    @field_validator("check_out_date")
    @classmethod
    def valid_stay(cls, value: date, info):
        start = info.data.get("check_in_date")
        if start and value <= start:
            raise ValueError("check_out_date must be after check_in_date")
        return value


class BlockUpdateRequest(PropertyScopedRequest):
    block_name: str | None = None
    company_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    room_type: str | None = None
    rooms: int | None = Field(None, ge=1)
    rate_code: str | None = None
    notes: str | None = None
    status: str | None = None


class BlockQuoteRequest(PropertyScopedRequest):
    quoted_amount: float | None = Field(None, ge=0)


class BlockDepositRequest(PropertyScopedRequest):
    deposit_amount: float | None = Field(None, ge=0)


class BlockCancelRequest(PropertyScopedRequest):
    reason: str = Field(..., min_length=3)


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables WHERE table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _ensure_reservation_columns(db: Session) -> None:
    for statement in [
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_phone VARCHAR(80)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS nights INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS adults INTEGER DEFAULT 1",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS children INTEGER DEFAULT 0",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reservation_type VARCHAR(80)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS rate_code VARCHAR(40)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guarantee_type VARCHAR(80)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS deposit_required BOOLEAN DEFAULT FALSE",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancellation_policy TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS special_requests TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS vip_notes TEXT",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS company_name VARCHAR(180)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS travel_agent_name VARCHAR(180)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_name VARCHAR(180)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmation_status VARCHAR(80)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_profile_id INTEGER",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guest_id VARCHAR(80)",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
    ]:
        db.execute(text(statement))


def _ensure_guest_notification_outbox(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_notification_outbox (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER,
                public_request_id INTEGER,
                property_code VARCHAR(20),
                channel VARCHAR(50),
                recipient VARCHAR(255),
                action VARCHAR(100),
                message TEXT,
                business_date DATE,
                status VARCHAR(50) DEFAULT 'queued',
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
    )


def _normalize_room_key(room_type: str | None) -> str:
    value = str(room_type or "").strip().lower()
    if not value:
        return "standard"
    for key in ["suite", "family", "deluxe", "twin", "standard"]:
        if key in value:
            return key
    return value


def _generate_confirmation_id(property_code: str) -> str:
    prefix = "".join(ch for ch in property_code.upper() if ch.isalnum())[:4] or "GUZO"
    return f"{prefix}-{date.today().strftime('%y%m%d')}-{__import__('secrets').token_hex(3).upper()}"


def _get_hotel_id(db: Session, property_code: str) -> int | None:
    if not _table_exists(db, "hotels"):
        return None
    row = db.execute(
        text("SELECT id FROM hotels WHERE property_code = :property_code LIMIT 1"),
        {"property_code": property_code},
    ).first()
    return int(row[0]) if row else None


def calculate_reservation_availability(
    db: Session,
    *,
    property_code: str,
    check_in_date: date,
    check_out_date: date,
    room_type: str | None,
    rooms: int = 1,
) -> dict[str, Any]:
    if check_out_date <= check_in_date:
        raise HTTPException(status_code=400, detail="check_out_date must be after check_in_date")

    room_key = _normalize_room_key(room_type)
    total_rooms = 0
    if _table_exists(db, "rooms"):
        columns = _table_columns(db, "rooms")
        room_type_expr = "room_type" if "room_type" in columns else "'Standard Room'"
        status_expr = (
            "COALESCE(status, housekeeping_status, hk_status, 'in_service')"
            if {"status", "housekeeping_status", "hk_status"}.issubset(columns)
            else "COALESCE(status, 'in_service')"
            if "status" in columns
            else "COALESCE(housekeeping_status, 'in_service')"
            if "housekeeping_status" in columns
            else "'in_service'"
        )
        total_rooms = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM rooms
                    WHERE property_code = :property_code
                      AND LOWER({room_type_expr}) LIKE :room_pattern
                      AND LOWER({status_expr}) NOT IN (
                        'out_of_order', 'out of order', 'ooo',
                        'out_of_service', 'out of service', 'oos',
                        'maintenance'
                      )
                    """
                ),
                {
                    "property_code": property_code,
                    "room_pattern": f"%{room_key}%",
                },
            ).scalar()
            or 0
        )

    active_bookings = 0
    if _table_exists(db, "bookings"):
        active_bookings = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM bookings
                    WHERE property_code = :property_code
                      AND LOWER(COALESCE(room_type, 'standard')) LIKE :room_pattern
                      AND LOWER(COALESCE(booking_status, '')) IN (
                        'confirmed', 'reserved', 'pending', 'pending_guarantee',
                        'in_house', 'checked_in'
                      )
                      AND check_in_date < :check_out_date
                      AND check_out_date > :check_in_date
                    """
                ),
                {
                    "property_code": property_code,
                    "room_pattern": f"%{room_key}%",
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                },
            ).scalar()
            or 0
        )

    available_rooms = max(total_rooms - active_bookings, 0)
    requested_rooms = max(int(rooms or 1), 1)
    return {
        "property_code": property_code,
        "check_in_date": check_in_date.isoformat(),
        "check_out_date": check_out_date.isoformat(),
        "room_type": room_type or "Standard Room",
        "total_rooms": total_rooms,
        "active_bookings": active_bookings,
        "available_rooms": available_rooms,
        "requested_rooms": requested_rooms,
        "is_available": available_rooms >= requested_rooms,
    }


def duplicate_reservation_warnings(
    db: Session,
    *,
    property_code: str,
    guest_name: str,
    guest_email: str | None,
    guest_phone: str | None,
    check_in_date: date,
    source: str | None,
) -> list[dict[str, Any]]:
    if not _table_exists(db, "bookings"):
        return []
    columns = _table_columns(db, "bookings")
    phone_filter = "OR (:guest_phone IS NOT NULL AND LOWER(COALESCE(guest_phone, '')) = LOWER(:guest_phone))" if "guest_phone" in columns else ""
    source_filter = "OR (:source IS NOT NULL AND LOWER(COALESCE(source, '')) = LOWER(:source))" if "source" in columns else ""
    rows = db.execute(
        text(
            f"""
            SELECT id, guest_name, guest_email, check_in_date, source, booking_status
            FROM bookings
            WHERE property_code = :property_code
              AND check_in_date = :check_in_date
              AND LOWER(COALESCE(booking_status, '')) NOT IN ('cancelled', 'checked_out', 'no_show', 'no-show')
              AND (
                LOWER(COALESCE(guest_name, '')) = LOWER(:guest_name)
                OR (:guest_email IS NOT NULL AND LOWER(COALESCE(guest_email, '')) = LOWER(:guest_email))
                {phone_filter}
                {source_filter}
              )
            ORDER BY id DESC
            LIMIT 10
            """
        ),
        {
            "property_code": property_code,
            "guest_name": guest_name,
            "guest_email": guest_email,
            "guest_phone": guest_phone,
            "check_in_date": check_in_date,
            "source": source,
        },
    ).mappings().all()
    return [
        {
            "booking_id": row["id"],
            "guest_name": row["guest_name"],
            "guest_email": row["guest_email"],
            "arrival_date": row["check_in_date"].isoformat() if row["check_in_date"] else None,
            "source": row["source"],
            "status": row["booking_status"],
            "warning": "Possible duplicate reservation for same guest/contact/source and arrival date.",
        }
        for row in rows
    ]


def _confirmation_message(guest_name: str, confirmation_id: str, check_in: date, check_out: date, room_type: str | None) -> str:
    return (
        f"Dear {guest_name}, your reservation is confirmed. "
        f"Confirmation Number: {confirmation_id}. "
        f"Stay: {check_in.isoformat()} to {check_out.isoformat()}. "
        f"Room Type: {room_type or 'TBD'}. "
        "Thank you for choosing Guzo PMS hotel operations."
    )


@router.post("/availability-quote")
def availability_quote(
    payload: ReservationAvailabilityRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    require_pms_permission(
        db,
        permission_key="reservations.review_booking_request",
        property_code=payload.property_code,
        user_email=x_pms_user_email,
    )
    availability = calculate_reservation_availability(
        db,
        property_code=payload.property_code,
        check_in_date=payload.check_in_date,
        check_out_date=payload.check_out_date,
        room_type=payload.room_type,
        rooms=payload.rooms,
    )
    quote = quote_stay(
        property_code=payload.property_code,
        check_in=payload.check_in_date,
        check_out=payload.check_out_date,
        room_type=payload.room_type,
        rooms=payload.rooms,
        adults=payload.adults,
        children=payload.children,
        rate_code=payload.rate_code,
        db=db,
    )
    return {"availability": availability, "quote": quote}


def _create_reservation_in_transaction(
    payload: ReservationCreateRequest,
    db: Session,
    x_pms_user_email: str | None,
    *,
    commit: bool,
):
    property_code = payload.property_code
    actor = require_pms_permission(
        db,
        permission_key="reservations.convert_booking",
        property_code=property_code,
        user_email=x_pms_user_email,
    )
    _ensure_reservation_columns(db)
    _ensure_guest_notification_outbox(db)
    availability = calculate_reservation_availability(
        db,
        property_code=property_code,
        check_in_date=payload.check_in_date,
        check_out_date=payload.check_out_date,
        room_type=payload.room_type,
        rooms=payload.rooms,
    )
    quote = quote_stay(
        property_code=property_code,
        check_in=payload.check_in_date,
        check_out=payload.check_out_date,
        room_type=payload.room_type,
        rooms=payload.rooms,
        adults=payload.adults,
        children=payload.children,
        rate_code=payload.rate_code,
        db=db,
    )
    duplicates = duplicate_reservation_warnings(
        db,
        property_code=property_code,
        guest_name=payload.guest_name,
        guest_email=payload.guest_email,
        guest_phone=payload.guest_phone,
        check_in_date=payload.check_in_date,
        source=payload.source,
    )
    if not availability["is_available"]:
        raise HTTPException(
            status_code=409,
            detail={"message": "Reservation would overbook the selected room type.", "availability": availability},
        )

    guest_profile = find_or_create_guest_profile(
        db,
        property_code=property_code,
        guest_name=payload.guest_name,
        email=payload.guest_email,
        phone=payload.guest_phone,
        vip_flag=bool(payload.vip_notes),
        preferences={
            "room_type": payload.room_type,
            "special_requests": payload.special_requests,
            "rate_code": payload.rate_code,
        },
        notes=payload.vip_notes or payload.notes,
    )
    confirmation_id = _generate_confirmation_id(property_code)
    nights = max((payload.check_out_date - payload.check_in_date).days, 1)
    notes = " | ".join(
        item
        for item in [
            payload.notes,
            f"Reservation Type: {payload.reservation_type}",
            f"Source: {payload.source}",
            f"Company: {payload.company_name}" if payload.company_name else None,
            f"Travel Agent: {payload.travel_agent_name}" if payload.travel_agent_name else None,
            f"Event: {payload.event_name}" if payload.event_name else None,
            f"Guarantee: {payload.guarantee_type}",
            f"Deposit Required: {quote['deposit_required_etb']}",
            f"Cancellation Policy: {payload.cancellation_policy or quote['cancellation_policy']}",
            f"Special Requests: {payload.special_requests}" if payload.special_requests else None,
            f"VIP Notes: {payload.vip_notes}" if payload.vip_notes else None,
        ]
        if item
    )
    row = db.execute(
        text(
            """
            INSERT INTO bookings (
                confirmation_id, hotel_id, guest_name, guest_email, guest_phone,
                property_code, check_in_date, check_out_date, nights, adults, children,
                room_type, rate_per_night_etb, total_revenue_etb, total_amount,
                booking_status, payment_status, source, channel, reservation_type,
                rate_code, guarantee_type, deposit_required, cancellation_policy,
                special_requests, vip_notes, company_name, travel_agent_name, event_name,
                confirmation_status, notes, created_at
            )
            VALUES (
                :confirmation_id, :hotel_id, :guest_name, :guest_email, :guest_phone,
                :property_code, :check_in_date, :check_out_date, :nights, :adults, :children,
                :room_type, :rate_per_night_etb, :total_revenue_etb, :total_amount,
                'confirmed', :payment_status, :source, :channel, :reservation_type,
                :rate_code, :guarantee_type, :deposit_required, :cancellation_policy,
                :special_requests, :vip_notes, :company_name, :travel_agent_name, :event_name,
                'confirmation_queued', :notes, CURRENT_TIMESTAMP
            )
            RETURNING id
            """
        ),
        {
            "confirmation_id": confirmation_id,
            "hotel_id": _get_hotel_id(db, property_code),
            "guest_name": payload.guest_name,
            "guest_email": payload.guest_email,
            "guest_phone": payload.guest_phone,
            "property_code": property_code,
            "check_in_date": payload.check_in_date,
            "check_out_date": payload.check_out_date,
            "nights": nights,
            "adults": payload.adults,
            "children": payload.children,
            "room_type": payload.room_type,
            "rate_per_night_etb": quote["nightly_rate_etb"],
            "total_revenue_etb": quote["gross_revenue_etb"],
            "total_amount": quote["gross_revenue_etb"],
            "payment_status": "pending_guarantee" if quote["guarantee_required"] else "pay_at_hotel",
            "source": payload.source,
            "channel": payload.source,
            "reservation_type": payload.reservation_type,
            "rate_code": payload.rate_code,
            "guarantee_type": payload.guarantee_type,
            "deposit_required": payload.deposit_required,
            "cancellation_policy": payload.cancellation_policy or quote["cancellation_policy"],
            "special_requests": payload.special_requests,
            "vip_notes": payload.vip_notes,
            "company_name": payload.company_name,
            "travel_agent_name": payload.travel_agent_name,
            "event_name": payload.event_name,
            "notes": notes,
        },
    ).first()
    booking_id = int(row[0])
    link_guest_profile_to_booking(db, booking_id=booking_id, guest_profile=guest_profile)
    message = _confirmation_message(
        payload.guest_name,
        confirmation_id,
        payload.check_in_date,
        payload.check_out_date,
        payload.room_type,
    )
    notification_status = queue_guest_notification(
        db,
        property_code=property_code,
        booking_id=booking_id,
        guest_profile=guest_profile,
        guest_email=payload.guest_email,
        guest_phone=payload.guest_phone,
        action="reservation_confirmation",
        message=message,
        business_date=payload.check_in_date,
    )
    if payload.vip_notes:
        queue_manager_alert(
            db,
            property_code=property_code,
            alert_type="vip_arrival",
            severity="high",
            message=f"VIP arrival flagged for {payload.guest_name}: {payload.vip_notes}",
            guest_profile=guest_profile,
            booking_id=booking_id,
            business_date=payload.check_in_date,
        )
    queue_prearrival_deposit_alert_if_needed(
        db,
        property_code=property_code,
        check_in_date=payload.check_in_date,
        payment_status="pending_guarantee" if quote["guarantee_required"] else "pay_at_hotel",
        guest_profile=guest_profile,
        booking_id=booking_id,
    )
    record_audit_log(
        db,
        action="reservation_created",
        entity_type="booking",
        entity_id=booking_id,
        property_code=property_code,
        business_date=payload.check_in_date,
        performed_by=actor["email"],
        details={"confirmation_id": confirmation_id, "availability": availability, "quote": quote},
    )
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor["email"],
        module="reservations",
        action="reservation_created",
        record_type="booking",
        record_id=booking_id,
        new_value={
            "confirmation_id": confirmation_id,
            "guest_id": guest_profile["guest_id"],
            "guest_name": payload.guest_name,
            "source": payload.source,
            "reservation_type": payload.reservation_type,
            "duplicates": duplicates,
        },
    )
    if commit:
        db.commit()
    return {
        "ok": True,
        "booking_id": booking_id,
        "confirmation_id": confirmation_id,
        "confirmation_status": "confirmation_queued",
        "availability": availability,
        "quote": quote,
        "duplicate_warnings": duplicates,
        "guest_id": guest_profile["guest_id"],
        "guest_notification_status": notification_status,
    }


@router.post("")
@router.post("/")
def create_reservation(
    payload: ReservationCreateRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    return _create_reservation_in_transaction(
        payload,
        db,
        x_pms_user_email,
        commit=True,
    )


@router.patch("/{booking_id}")
def update_reservation(
    booking_id: int,
    payload: ReservationUpdateRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="reservations.modify_booking",
        property_code=payload.property_code,
        user_email=x_pms_user_email,
    )
    _ensure_reservation_columns(db)
    row = db.execute(
        text("SELECT * FROM bookings WHERE id = :booking_id AND property_code = :property_code"),
        {"booking_id": booking_id, "property_code": payload.property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Reservation not found")
    updates = []
    params: dict[str, Any] = {"booking_id": booking_id, "property_code": payload.property_code}
    for field in [
        "guest_name",
        "guest_email",
        "guest_phone",
        "check_in_date",
        "check_out_date",
        "room_type",
        "rate_code",
        "guarantee_type",
        "special_requests",
        "vip_notes",
        "notes",
    ]:
        value = getattr(payload, field)
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    if not updates:
        return {"ok": True, "booking_id": booking_id, "message": "No changes submitted."}
    updates.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(
        text(
            f"""
            UPDATE bookings
            SET {', '.join(updates)}
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        params,
    )
    record_pms_audit_log(
        db,
        property_code=payload.property_code,
        user_email=actor["email"],
        module="reservations",
        action="reservation_modified",
        record_type="booking",
        record_id=booking_id,
        old_value=dict(row),
        new_value=params,
    )
    db.commit()
    return {"ok": True, "booking_id": booking_id}


@router.post("/{booking_id}/cancel")
def cancel_reservation(
    booking_id: int,
    payload: ReservationCancelRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="reservations.cancel_booking",
        property_code=payload.property_code,
        user_email=x_pms_user_email,
    )
    row = db.execute(
        text("SELECT booking_status FROM bookings WHERE id = :booking_id AND property_code = :property_code"),
        {"booking_id": booking_id, "property_code": payload.property_code},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Reservation not found")
    db.execute(
        text(
            """
            UPDATE bookings
            SET booking_status = 'cancelled',
                notes = NULLIF(CONCAT_WS(E'\n', NULLIF(notes, ''), :cancel_note), ''),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :booking_id
              AND property_code = :property_code
            """
        ),
        {
            "booking_id": booking_id,
            "property_code": payload.property_code,
            "cancel_note": f"Cancelled by Reservations: {payload.reason}",
        },
    )
    record_pms_audit_log(
        db,
        property_code=payload.property_code,
        user_email=actor["email"],
        module="reservations",
        action="reservation_cancelled",
        record_type="booking",
        record_id=booking_id,
        old_value={"booking_status": row["booking_status"]},
        new_value={"booking_status": "cancelled", "reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "booking_id": booking_id, "booking_status": "cancelled"}


@router.post("/waitlist")
def create_waitlist_item(payload: WaitlistCreateRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    if payload.check_out_date <= payload.check_in_date:
        raise HTTPException(status_code=400, detail="check_out_date must be after check_in_date")
    actor = require_pms_permission(db, permission_key="reservations.review_booking_request", property_code=payload.property_code, user_email=x_pms_user_email)
    item = persist_create_waitlist(db, payload.model_dump(), actor["email"])
    db.commit()
    return item


@router.get("/waitlist")
def get_waitlist_items(property_code: str, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = property_code.strip().upper()
    require_pms_permission(db, permission_key="reservations.review_booking_request", user_email=x_pms_user_email)
    return {"items": list_waitlist(db, code)}


@router.post("/waitlist/{item_id}/review")
def review_waitlist_item(item_id: int, payload: PropertyScopedRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.review_booking_request", property_code=payload.property_code, user_email=x_pms_user_email)
    item = get_waitlist(db, item_id, payload.property_code, for_update=True)
    if item["status"] in {"converted", "cancelled"}:
        raise HTTPException(status_code=409, detail=f"Cannot review a {item['status']} waitlist item")
    availability = calculate_reservation_availability(db, property_code=payload.property_code, check_in_date=item["check_in_date"], check_out_date=item["check_out_date"], room_type=item["room_type"], rooms=item["rooms"])
    updated = persist_review_waitlist(db, item, availability, actor["email"])
    db.commit()
    return {"item": updated, "availability": availability}


@router.post("/waitlist/{item_id}/convert")
def convert_waitlist_item(item_id: int, payload: PropertyScopedRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    try:
        actor = require_pms_permission(db, permission_key="reservations.convert_booking", property_code=payload.property_code, user_email=x_pms_user_email)
        item = get_waitlist(db, item_id, payload.property_code, for_update=True)
        if item["status"] == "converted":
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Waitlist item is already converted",
                    "converted_booking_id": item["converted_booking_id"],
                },
            )
        if item["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Cancelled waitlist items cannot be converted")
        availability = calculate_reservation_availability(db, property_code=payload.property_code, check_in_date=item["check_in_date"], check_out_date=item["check_out_date"], room_type=item["room_type"], rooms=item["rooms"])
        if not availability["is_available"]:
            raise HTTPException(status_code=409, detail={"message": "Waitlist item is not currently available", "availability": availability})
        result = _create_reservation_in_transaction(
            ReservationCreateRequest(
                property_code=payload.property_code,
                guest_name=item["guest_name"],
                guest_email=item["guest_email"],
                guest_phone=item["guest_phone"],
                check_in_date=item["check_in_date"],
                check_out_date=item["check_out_date"],
                room_type=item["room_type"],
                rooms=item["rooms"],
                adults=item["adults"],
                children=item["children"],
                rate_code=item["rate_code"],
                reservation_type="waitlist_conversion",
                source=item["source"],
                guarantee_type="deposit_required",
                deposit_required=True,
                notes=item["notes"],
            ),
            db,
            x_pms_user_email,
            commit=False,
        )
        updated = mark_waitlist_converted(db, item, result["booking_id"], actor["email"])
        db.commit()
        return {"item": updated, "reservation": result}
    except Exception:
        db.rollback()
        raise


@router.post("/waitlist/{item_id}/cancel")
def cancel_waitlist_item(item_id: int, payload: WaitlistCancelRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.cancel_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    item = get_waitlist(db, item_id, payload.property_code, for_update=True)
    updated = persist_cancel_waitlist(db, item, payload.reason, actor["email"])
    db.commit()
    return updated


@router.post("/blocks")
def create_reservation_block(payload: BlockCreateRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.convert_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    block = persist_create_block(db, payload.model_dump(), actor["email"])
    db.commit()
    return block


@router.get("/blocks")
def get_reservation_blocks(property_code: str, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    code = property_code.strip().upper()
    require_pms_permission(db, permission_key="reservations.review_booking_request", user_email=x_pms_user_email)
    return {"items": list_blocks(db, code)}


@router.patch("/blocks/{block_id}")
def update_reservation_block(block_id: int, payload: BlockUpdateRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.modify_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    block = get_block(db, block_id, payload.property_code, for_update=True)
    if block["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled blocks cannot be updated")
    allowed_statuses = {None, "tentative", "quoted", "deposit_requested", "confirmed", "cancelled"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid block status")
    updated = persist_update_block(db, block, payload.model_dump(exclude={"property_code"}, exclude_none=True), actor["email"])
    db.commit()
    return updated


@router.post("/blocks/{block_id}/quote")
def quote_reservation_block(block_id: int, payload: BlockQuoteRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.modify_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    block = get_block(db, block_id, payload.property_code, for_update=True)
    if block["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled blocks cannot be quoted")
    quote = quote_stay(property_code=payload.property_code, check_in=block["check_in_date"], check_out=block["check_out_date"], room_type=block["room_type"], rooms=block["rooms"], adults=block["rooms"], children=0, rate_code=block["rate_code"], db=db)
    amount = payload.quoted_amount if payload.quoted_amount is not None else float(quote["gross_revenue_etb"])
    updated = persist_update_block(db, block, {"status": "quoted", "quoted_amount": amount}, actor["email"], action="reservation_block_quoted")
    db.commit()
    return {"item": updated, "quote": quote}


@router.post("/blocks/{block_id}/request-deposit")
def request_block_deposit(block_id: int, payload: BlockDepositRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.modify_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    block = get_block(db, block_id, payload.property_code, for_update=True)
    if block["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled blocks cannot request a deposit")
    base = float(block.get("quoted_amount") or 0)
    amount = payload.deposit_amount if payload.deposit_amount is not None else round(base * 0.3, 2)
    updated = persist_update_block(db, block, {"status": "deposit_requested", "deposit_amount": amount}, actor["email"], action="reservation_block_deposit_requested")
    db.commit()
    return updated


@router.post("/blocks/{block_id}/cancel")
def cancel_reservation_block(block_id: int, payload: BlockCancelRequest, db: Session = Depends(get_db), x_pms_user_email: str | None = Header(None)):
    actor = require_pms_permission(db, permission_key="reservations.cancel_booking", property_code=payload.property_code, user_email=x_pms_user_email)
    block = get_block(db, block_id, payload.property_code, for_update=True)
    updated = persist_update_block(db, block, {"status": "cancelled", "cancellation_reason": payload.reason}, actor["email"], action="reservation_block_cancelled")
    db.commit()
    return updated
