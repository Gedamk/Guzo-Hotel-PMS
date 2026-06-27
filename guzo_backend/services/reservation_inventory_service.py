from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.pms_security_service import record_pms_audit_log


def ensure_reservation_inventory_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reservation_waitlist (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                guest_name VARCHAR(150) NOT NULL,
                guest_email VARCHAR(255),
                guest_phone VARCHAR(80),
                check_in_date DATE NOT NULL,
                check_out_date DATE NOT NULL,
                room_type VARCHAR(100),
                rooms INTEGER DEFAULT 1,
                adults INTEGER DEFAULT 1,
                children INTEGER DEFAULT 0,
                rate_code VARCHAR(40),
                source VARCHAR(80),
                notes TEXT,
                status VARCHAR(40) DEFAULT 'open',
                available_rooms INTEGER,
                availability_checked_at TIMESTAMPTZ,
                converted_booking_id INTEGER,
                converted_at TIMESTAMPTZ,
                cancellation_reason TEXT,
                cancelled_at TIMESTAMPTZ,
                created_by VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reservation_blocks (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                block_name VARCHAR(180) NOT NULL,
                company_name VARCHAR(180),
                contact_name VARCHAR(180),
                contact_email VARCHAR(255),
                contact_phone VARCHAR(80),
                check_in_date DATE NOT NULL,
                check_out_date DATE NOT NULL,
                room_type VARCHAR(100),
                rooms INTEGER NOT NULL DEFAULT 1,
                rate_code VARCHAR(40),
                quoted_amount NUMERIC(18, 2),
                deposit_amount NUMERIC(18, 2),
                notes TEXT,
                status VARCHAR(40) DEFAULT 'tentative',
                quoted_at TIMESTAMPTZ,
                deposit_requested_at TIMESTAMPTZ,
                confirmed_at TIMESTAMPTZ,
                cancellation_reason TEXT,
                cancelled_at TIMESTAMPTZ,
                created_by VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )
            """
        )
    )


def _record(db: Session, *, property_code: str, actor_email: str, action: str, record_type: str, record_id: int, old_value: dict | None = None, new_value: dict | None = None) -> None:
    record_pms_audit_log(
        db,
        property_code=property_code,
        user_email=actor_email,
        module="reservations",
        action=action,
        record_type=record_type,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
    )


def list_waitlist(db: Session, property_code: str) -> list[dict[str, Any]]:
    ensure_reservation_inventory_tables(db)
    return [dict(row) for row in db.execute(text("SELECT * FROM reservation_waitlist WHERE property_code = :property_code ORDER BY created_at DESC, id DESC"), {"property_code": property_code}).mappings().all()]


def get_waitlist(db: Session, item_id: int, property_code: str, *, for_update: bool = False) -> dict[str, Any]:
    ensure_reservation_inventory_tables(db)
    suffix = " FOR UPDATE" if for_update else ""
    row = db.execute(text(f"SELECT * FROM reservation_waitlist WHERE id = :item_id AND property_code = :property_code{suffix}"), {"item_id": item_id, "property_code": property_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Waitlist item not found")
    return dict(row)


def create_waitlist(db: Session, values: dict[str, Any], actor_email: str) -> dict[str, Any]:
    ensure_reservation_inventory_tables(db)
    row = db.execute(
        text("""
            INSERT INTO reservation_waitlist (
                property_code, guest_name, guest_email, guest_phone, check_in_date,
                check_out_date, room_type, rooms, adults, children, rate_code,
                source, notes, status, created_by
            ) VALUES (
                :property_code, :guest_name, :guest_email, :guest_phone, :check_in_date,
                :check_out_date, :room_type, :rooms, :adults, :children, :rate_code,
                :source, :notes, 'open', :created_by
            ) RETURNING *
        """),
        {**values, "created_by": actor_email},
    ).mappings().first()
    result = dict(row)
    _record(db, property_code=values["property_code"], actor_email=actor_email, action="waitlist_created", record_type="reservation_waitlist", record_id=result["id"], new_value=result)
    return result


def review_waitlist(db: Session, item: dict[str, Any], availability: dict[str, Any], actor_email: str) -> dict[str, Any]:
    status = "available" if availability["is_available"] else "open"
    row = db.execute(
        text("""
            UPDATE reservation_waitlist
            SET status = :status, available_rooms = :available_rooms,
                availability_checked_at = now(), updated_at = now()
            WHERE id = :item_id AND property_code = :property_code
            RETURNING *
        """),
        {"status": status, "available_rooms": availability["available_rooms"], "item_id": item["id"], "property_code": item["property_code"]},
    ).mappings().first()
    result = dict(row)
    _record(db, property_code=item["property_code"], actor_email=actor_email, action="waitlist_availability_reviewed", record_type="reservation_waitlist", record_id=item["id"], old_value=item, new_value={"status": status, "availability": availability})
    return result


def mark_waitlist_converted(db: Session, item: dict[str, Any], booking_id: int, actor_email: str) -> dict[str, Any]:
    row = db.execute(
        text("""
            UPDATE reservation_waitlist
            SET status = 'converted', converted_booking_id = :booking_id,
                converted_at = now(), updated_at = now()
            WHERE id = :item_id AND property_code = :property_code
            RETURNING *
        """),
        {"booking_id": booking_id, "item_id": item["id"], "property_code": item["property_code"]},
    ).mappings().first()
    result = dict(row)
    _record(db, property_code=item["property_code"], actor_email=actor_email, action="waitlist_converted", record_type="reservation_waitlist", record_id=item["id"], old_value=item, new_value={"status": "converted", "booking_id": booking_id})
    return result


def cancel_waitlist(db: Session, item: dict[str, Any], reason: str, actor_email: str) -> dict[str, Any]:
    if item["status"] == "converted":
        raise HTTPException(status_code=409, detail="Converted waitlist items cannot be cancelled")
    row = db.execute(text("UPDATE reservation_waitlist SET status = 'cancelled', cancellation_reason = :reason, cancelled_at = now(), updated_at = now() WHERE id = :item_id AND property_code = :property_code RETURNING *"), {"reason": reason, "item_id": item["id"], "property_code": item["property_code"]}).mappings().first()
    result = dict(row)
    _record(db, property_code=item["property_code"], actor_email=actor_email, action="waitlist_cancelled", record_type="reservation_waitlist", record_id=item["id"], old_value=item, new_value={"status": "cancelled", "reason": reason})
    return result


def list_blocks(db: Session, property_code: str) -> list[dict[str, Any]]:
    ensure_reservation_inventory_tables(db)
    return [dict(row) for row in db.execute(text("SELECT * FROM reservation_blocks WHERE property_code = :property_code ORDER BY created_at DESC, id DESC"), {"property_code": property_code}).mappings().all()]


def get_block(db: Session, block_id: int, property_code: str, *, for_update: bool = False) -> dict[str, Any]:
    ensure_reservation_inventory_tables(db)
    suffix = " FOR UPDATE" if for_update else ""
    row = db.execute(text(f"SELECT * FROM reservation_blocks WHERE id = :block_id AND property_code = :property_code{suffix}"), {"block_id": block_id, "property_code": property_code}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Reservation block not found")
    return dict(row)


def create_block(db: Session, values: dict[str, Any], actor_email: str) -> dict[str, Any]:
    ensure_reservation_inventory_tables(db)
    row = db.execute(text("""
        INSERT INTO reservation_blocks (
            property_code, block_name, company_name, contact_name, contact_email,
            contact_phone, check_in_date, check_out_date, room_type, rooms,
            rate_code, notes, status, created_by
        ) VALUES (
            :property_code, :block_name, :company_name, :contact_name, :contact_email,
            :contact_phone, :check_in_date, :check_out_date, :room_type, :rooms,
            :rate_code, :notes, 'tentative', :created_by
        ) RETURNING *
    """), {**values, "created_by": actor_email}).mappings().first()
    result = dict(row)
    _record(db, property_code=values["property_code"], actor_email=actor_email, action="reservation_block_created", record_type="reservation_block", record_id=result["id"], new_value=result)
    return result


def update_block(db: Session, block: dict[str, Any], values: dict[str, Any], actor_email: str, *, action: str = "reservation_block_updated") -> dict[str, Any]:
    allowed = {"block_name", "company_name", "contact_name", "contact_email", "contact_phone", "check_in_date", "check_out_date", "room_type", "rooms", "rate_code", "notes", "status", "quoted_amount", "deposit_amount", "cancellation_reason"}
    updates = {key: value for key, value in values.items() if key in allowed and value is not None}
    if not updates:
        return block
    assignments = [f"{key} = :{key}" for key in updates]
    if updates.get("status") == "quoted": assignments.append("quoted_at = now()")
    if updates.get("status") == "deposit_requested": assignments.append("deposit_requested_at = now()")
    if updates.get("status") == "confirmed": assignments.append("confirmed_at = now()")
    if updates.get("status") == "cancelled": assignments.append("cancelled_at = now()")
    assignments.append("updated_at = now()")
    params = {**updates, "block_id": block["id"], "property_code": block["property_code"]}
    row = db.execute(text(f"UPDATE reservation_blocks SET {', '.join(assignments)} WHERE id = :block_id AND property_code = :property_code RETURNING *"), params).mappings().first()
    result = dict(row)
    _record(db, property_code=block["property_code"], actor_email=actor_email, action=action, record_type="reservation_block", record_id=block["id"], old_value=block, new_value=updates)
    return result
