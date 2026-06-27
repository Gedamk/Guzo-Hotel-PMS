from __future__ import annotations

from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

load_dotenv()

from guzo_backend.core.postgres_db import SessionLocal
from guzo_backend.main import app
from guzo_backend.api import reservations_api
from guzo_backend.services.pms_security_service import ensure_pms_security_tables


client = TestClient(app)
HEADERS = {"X-PMS-User-Email": "admin@guzo.local"}


def _setup_property() -> tuple[str, str]:
    code = f"RW{uuid4().hex[:6].upper()}"
    other = f"RO{uuid4().hex[:6].upper()}"
    with SessionLocal() as db:
        ensure_pms_security_tables(db, code)
        db.execute(text("""
            INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
            VALUES ('Reservation QA Admin', 'admin@guzo.local', 'admin', NULL, TRUE)
            ON CONFLICT (email) DO UPDATE SET role_key = 'admin', is_active = TRUE
        """))
        hotel_id = db.execute(text("INSERT INTO hotels (property_code, name) VALUES (:code, :name) ON CONFLICT (property_code) DO UPDATE SET name = EXCLUDED.name RETURNING id"), {"code": code, "name": f"QA {code}"}).scalar()
        for number in range(101, 105):
            db.execute(text("INSERT INTO rooms (hotel_id, property_code, room_number, room_type, floor) VALUES (:hotel_id, :code, :number, 'Standard Room', 1)"), {"hotel_id": hotel_id, "code": code, "number": str(number)})
        db.commit()
    return code, other


def _cleanup(code: str) -> None:
    with SessionLocal() as db:
        for table in ["guest_notification_outbox", "audit_logs", "pms_audit_logs", "reservation_waitlist", "reservation_blocks", "bookings", "rooms"]:
            if db.execute(text("SELECT to_regclass(:table)"), {"table": table}).scalar():
                db.execute(text(f"DELETE FROM {table} WHERE property_code = :code"), {"code": code})
        db.execute(text("DELETE FROM hotels WHERE property_code = :code"), {"code": code})
        db.commit()


def test_waitlist_create_list_review_convert_cancel_filter_and_audit() -> None:
    code, other = _setup_property()
    try:
        payload = {
            "property_code": code,
            "guest_name": "Waitlist QA Guest",
            "check_in_date": "2026-07-10",
            "check_out_date": "2026-07-12",
            "room_type": "Standard Room",
            "rooms": 1,
            "adults": 2,
            "children": 0,
            "rate_code": "BAR",
            "source": "qa",
            "notes": "Persistence test",
        }
        created = client.post("/reservations/waitlist", json=payload, headers=HEADERS)
        assert created.status_code == 200, created.text
        item_id = created.json()["id"]
        assert created.json()["status"] == "open"

        listed = client.get("/reservations/waitlist", params={"property_code": code}, headers=HEADERS)
        assert listed.status_code == 200
        assert [row["id"] for row in listed.json()["items"]] == [item_id]
        filtered = client.get("/reservations/waitlist", params={"property_code": other}, headers=HEADERS)
        assert filtered.status_code == 200
        assert filtered.json()["items"] == []

        reviewed = client.post(f"/reservations/waitlist/{item_id}/review", json={"property_code": code}, headers=HEADERS)
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["item"]["status"] == "available"

        converted = client.post(f"/reservations/waitlist/{item_id}/convert", json={"property_code": code}, headers=HEADERS)
        assert converted.status_code == 200, converted.text
        assert converted.json()["item"]["status"] == "converted"
        assert converted.json()["item"]["converted_booking_id"]

        second_conversion = client.post(f"/reservations/waitlist/{item_id}/convert", json={"property_code": code}, headers=HEADERS)
        assert second_conversion.status_code == 409
        assert second_conversion.json()["detail"]["message"] == "Waitlist item is already converted"
        assert second_conversion.json()["detail"]["converted_booking_id"] == converted.json()["item"]["converted_booking_id"]
        with SessionLocal() as db:
            assert db.execute(text("SELECT COUNT(*) FROM bookings WHERE property_code = :code AND reservation_type = 'waitlist_conversion'"), {"code": code}).scalar() == 1

        cancel_created = client.post("/reservations/waitlist", json={**payload, "guest_name": "Cancel QA Guest"}, headers=HEADERS).json()
        cancelled = client.post(f"/reservations/waitlist/{cancel_created['id']}/cancel", json={"property_code": code, "reason": "Guest withdrew request"}, headers=HEADERS)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        with SessionLocal() as db:
            actions = set(db.execute(text("SELECT action FROM pms_audit_logs WHERE property_code = :code AND module = 'reservations'"), {"code": code}).scalars().all())
        assert {"waitlist_created", "waitlist_availability_reviewed", "waitlist_converted", "waitlist_cancelled"}.issubset(actions)
    finally:
        _cleanup(code)


def test_waitlist_conversion_rolls_back_booking_and_status_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    code, _ = _setup_property()
    try:
        payload = {
            "property_code": code,
            "guest_name": "Rollback QA Guest",
            "check_in_date": "2026-09-10",
            "check_out_date": "2026-09-12",
            "room_type": "Standard Room",
            "rooms": 1,
            "adults": 1,
            "children": 0,
            "rate_code": "BAR",
            "source": "qa",
            "notes": "Force rollback after booking insert",
        }
        created = client.post("/reservations/waitlist", json=payload, headers=HEADERS)
        assert created.status_code == 200
        item_id = created.json()["id"]

        def fail_after_booking(*args, **kwargs):
            raise RuntimeError("forced waitlist status failure")

        monkeypatch.setattr(reservations_api, "mark_waitlist_converted", fail_after_booking)
        with pytest.raises(RuntimeError, match="forced waitlist status failure"):
            client.post(f"/reservations/waitlist/{item_id}/convert", json={"property_code": code}, headers=HEADERS)

        with SessionLocal() as db:
            item = db.execute(text("SELECT status, converted_booking_id FROM reservation_waitlist WHERE id = :item_id AND property_code = :code"), {"item_id": item_id, "code": code}).mappings().one()
            booking_count = db.execute(text("SELECT COUNT(*) FROM bookings WHERE property_code = :code AND reservation_type = 'waitlist_conversion'"), {"code": code}).scalar()
            conversion_audits = db.execute(text("SELECT COUNT(*) FROM pms_audit_logs WHERE property_code = :code AND action IN ('reservation_created', 'waitlist_converted')"), {"code": code}).scalar()
        assert item["status"] == "open"
        assert item["converted_booking_id"] is None
        assert booking_count == 0
        assert conversion_audits == 0
    finally:
        _cleanup(code)


def test_block_create_list_update_quote_deposit_cancel_filter_and_audit() -> None:
    code, other = _setup_property()
    try:
        payload = {
            "property_code": code,
            "block_name": "QA Conference Block",
            "company_name": "QA Company",
            "contact_name": "Block Coordinator",
            "check_in_date": "2026-08-01",
            "check_out_date": "2026-08-04",
            "room_type": "Standard Room",
            "rooms": 3,
            "rate_code": "GRP10",
            "notes": "Group persistence test",
        }
        created = client.post("/reservations/blocks", json=payload, headers=HEADERS)
        assert created.status_code == 200, created.text
        block_id = created.json()["id"]
        assert created.json()["status"] == "tentative"

        listed = client.get("/reservations/blocks", params={"property_code": code}, headers=HEADERS)
        assert [row["id"] for row in listed.json()["items"]] == [block_id]
        filtered = client.get("/reservations/blocks", params={"property_code": other}, headers=HEADERS)
        assert filtered.status_code == 200
        assert filtered.json()["items"] == []

        updated = client.patch(f"/reservations/blocks/{block_id}", json={"property_code": code, "rooms": 4, "notes": "Updated room block"}, headers=HEADERS)
        assert updated.status_code == 200
        assert updated.json()["rooms"] == 4

        quoted = client.post(f"/reservations/blocks/{block_id}/quote", json={"property_code": code, "quoted_amount": 24000}, headers=HEADERS)
        assert quoted.status_code == 200, quoted.text
        assert quoted.json()["item"]["status"] == "quoted"

        deposit = client.post(f"/reservations/blocks/{block_id}/request-deposit", json={"property_code": code, "deposit_amount": 7200}, headers=HEADERS)
        assert deposit.status_code == 200
        assert deposit.json()["status"] == "deposit_requested"

        confirmed = client.patch(f"/reservations/blocks/{block_id}", json={"property_code": code, "status": "confirmed"}, headers=HEADERS)
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        cancelled = client.post(f"/reservations/blocks/{block_id}/cancel", json={"property_code": code, "reason": "Group cancelled event"}, headers=HEADERS)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        with SessionLocal() as db:
            actions = set(db.execute(text("SELECT action FROM pms_audit_logs WHERE property_code = :code AND module = 'reservations'"), {"code": code}).scalars().all())
        assert {"reservation_block_created", "reservation_block_updated", "reservation_block_quoted", "reservation_block_deposit_requested", "reservation_block_cancelled"}.issubset(actions)
    finally:
        _cleanup(code)


def test_new_and_update_reservation_still_work() -> None:
    code, _ = _setup_property()
    try:
        created = client.post(
            "/reservations",
            json={
                "property_code": code,
                "guest_name": "New Reservation QA Guest",
                "check_in_date": "2026-10-10",
                "check_out_date": "2026-10-12",
                "room_type": "Standard Room",
                "rooms": 1,
                "adults": 2,
                "children": 0,
                "rate_code": "BAR",
                "reservation_type": "individual_room",
                "source": "qa",
                "guarantee_type": "deposit_required",
                "deposit_required": True,
                "notes": "Created by final reservation workflow QA",
            },
            headers=HEADERS,
        )
        assert created.status_code == 200, created.text
        booking_id = created.json()["booking_id"]

        updated = client.patch(
            f"/reservations/{booking_id}",
            json={
                "property_code": code,
                "guest_name": "Updated Reservation QA Guest",
                "notes": "Updated by final reservation workflow QA",
            },
            headers=HEADERS,
        )
        assert updated.status_code == 200, updated.text

        listed = client.get(
            "/frontdesk/bookings",
            params={"scope": "touches", "date": "2026-10-10", "property": code},
            headers=HEADERS,
        )
        assert listed.status_code == 200, listed.text
        row = next(item for item in listed.json() if item["id"] == booking_id)
        assert row["guest_name"] == "Updated Reservation QA Guest"
        assert row["property_code"] == code
    finally:
        _cleanup(code)


def test_xxx001_does_not_leak_other_property_reservations_or_rooms() -> None:
    property_code = "XXX001"
    waitlist = client.get("/reservations/waitlist", params={"property_code": property_code}, headers=HEADERS)
    blocks = client.get("/reservations/blocks", params={"property_code": property_code}, headers=HEADERS)
    bookings = client.get("/frontdesk/bookings", params={"scope": "touches", "date": "2026-06-19", "property": property_code}, headers=HEADERS)
    rooms = client.get("/rooms/status-board", params={"property_code": property_code, "date": "2026-06-19"}, headers=HEADERS)

    for response in [waitlist, blocks, bookings, rooms]:
        assert response.status_code == 200, response.text

    scoped_rows = waitlist.json()["items"] + blocks.json()["items"] + bookings.json() + rooms.json()
    assert all(row.get("property_code") == property_code for row in scoped_rows)
    assert not any(row.get("property_code") in {"DRE001", "NN002"} for row in scoped_rows)
