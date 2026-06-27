from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

load_dotenv()

from guzo_backend.core.postgres_db import SessionLocal
from guzo_backend.main import app


ADMIN_HEADERS = {"X-PMS-User-Email": "admin@guzo.local"}


def _property_payload(code: str) -> dict:
    return {
        "name": f"QA Property {code}",
        "code": code,
        "address": "100 QA Avenue",
        "city": "Addis Ababa",
        "country": "Ethiopia",
        "timezone": "Africa/Addis_Ababa",
        "currency": "ETB",
        "phone": "+251 11 555 0101",
        "email": f"{code.lower()}@example.test",
        "isActive": True,
        "onboardingStatus": "not_started",
    }


def _audit_count(action: str, record_id: int) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pms_audit_logs
                    WHERE module = 'admin'
                      AND action = :action
                      AND record_type = 'hotel_property'
                      AND record_id = :record_id
                    """
                ),
                {"action": action, "record_id": str(record_id)},
            ).scalar()
            or 0
        )


def _delete_property(property_id: int) -> None:
    with SessionLocal() as db:
        code = db.execute(
            text("SELECT property_code FROM hotel_properties WHERE id = :property_id"),
            {"property_id": property_id},
        ).scalar()
        if code:
            if db.execute(text("SELECT to_regclass('pms_user_property_assignments')")).scalar():
                db.execute(
                    text("DELETE FROM pms_user_property_assignments WHERE property_code = :code"),
                    {"code": code},
                )
            for table in [
                "rooms",
                "rate_plans",
                "tax_service_rules",
                "deposit_policies",
                "ingredients",
                "pms_users",
            ]:
                db.execute(text(f"DELETE FROM {table} WHERE property_code = :code"), {"code": code})
            db.execute(text("DELETE FROM hotels WHERE property_code = :code"), {"code": code})
        db.execute(
            text("DELETE FROM hotel_properties WHERE id = :property_id"),
            {"property_id": property_id},
        )
        db.commit()


def _delete_user(email: str) -> None:
    with SessionLocal() as db:
        if db.execute(text("SELECT to_regclass('pms_user_property_assignments')")).scalar():
            db.execute(
                text("DELETE FROM pms_user_property_assignments WHERE LOWER(user_email) = LOWER(:email)"),
                {"email": email},
            )
        db.execute(
            text("DELETE FROM pms_users WHERE LOWER(email) = LOWER(:email)"),
            {"email": email},
        )
        db.commit()


def _create_pms_user(email: str, property_code: str | None, *, role_key: str = "admin", is_active: bool = True) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES (:full_name, LOWER(:email), :role_key, :property_code, :is_active)
                ON CONFLICT (email) DO UPDATE
                SET role_key = EXCLUDED.role_key,
                    property_code = EXCLUDED.property_code,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "full_name": f"QA User {email}",
                "email": email,
                "role_key": role_key,
                "property_code": property_code,
                "is_active": is_active,
            },
        )
        db.commit()


def _assignment_exists(email: str, property_code: str) -> bool:
    with SessionLocal() as db:
        return bool(
            db.execute(
                text(
                    """
                    SELECT 1
                    FROM pms_user_property_assignments
                    WHERE LOWER(user_email) = LOWER(:email)
                      AND property_code = :property_code
                    LIMIT 1
                    """
                ),
                {"email": email, "property_code": property_code},
            ).first()
        )


def _seed_go_live_setup(code: str) -> None:
    with SessionLocal() as db:
        hotel_id = db.execute(
            text(
                """
                INSERT INTO hotels (property_code, name)
                VALUES (:code, :name)
                ON CONFLICT (property_code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """
            ),
            {"code": code, "name": f"QA Hotel {code}"},
        ).scalar()
        db.execute(
            text(
                """
                INSERT INTO rooms (hotel_id, property_code, room_number, room_type, floor)
                VALUES (:hotel_id, :code, '101', 'Standard Room', 1)
                """
            ),
            {"code": code, "hotel_id": hotel_id},
        )
        db.execute(
            text(
                """
                INSERT INTO rate_plans (property_code, code, name, multiplier, is_active)
                VALUES (:code, 'BAR', 'Best Available Rate', 1, TRUE)
                """
            ),
            {"code": code},
        )
        db.execute(
            text(
                """
                INSERT INTO tax_service_rules (property_code, rule_name, tax_percent, service_charge_percent, is_active)
                VALUES (:code, 'Standard Tax / Service', 0.15, 0.10, TRUE)
                """
            ),
            {"code": code},
        )
        db.execute(
            text(
                """
                INSERT INTO pms_users (full_name, email, role_key, property_code, is_active)
                VALUES
                  ('QA General Manager', :gm_email, 'general_manager', :code, TRUE),
                  ('QA Finance Cashier', :cashier_email, 'finance_cashier', :code, TRUE)
                """
            ),
            {
                "code": code,
                "gm_email": f"gm-{code.lower()}@example.test",
                "cashier_email": f"cashier-{code.lower()}@example.test",
            },
        )
        db.execute(
            text(
                """
                INSERT INTO ingredients (
                    property_code, name, category, unit, purchase_price, cost_per_unit,
                    reorder_level, supplier_name
                )
                VALUES (:code, 'Coffee Beans', 'Beverage', 'kg', 500, 500, 5, 'QA Supplier')
                """
            ),
            {"code": code},
        )
        db.commit()


def test_get_properties_returns_demo_hotels():
    with TestClient(app) as client:
        response = client.get("/properties")

    assert response.status_code == 200, response.text
    properties = {item["code"]: item for item in response.json()["properties"]}
    assert properties["DRE001"]["name"] == "Dream Big Hotel"
    assert properties["NN002"]["name"] == "N&N Hotel"


def test_admin_property_create_duplicate_update_status_and_audit():
    code = f"QA{uuid4().hex[:6].upper()}"
    payload = _property_payload(code)
    property_id = None

    try:
        with TestClient(app) as client:
            created_response = client.post("/admin/properties", json=payload, headers=ADMIN_HEADERS)
            duplicate_response = client.post("/admin/properties", json=payload, headers=ADMIN_HEADERS)

            assert created_response.status_code == 200, created_response.text
            created = created_response.json()["property"]
            property_id = created["id"]
            assert created["code"] == code
            assert duplicate_response.status_code == 409

            update_payload = {
                "name": f"Updated {code}",
                "address": "200 Updated QA Avenue",
                "city": "Bishoftu",
                "country": "Ethiopia",
                "timezone": "Africa/Addis_Ababa",
                "currency": "USD",
                "phone": "+251 11 555 0202",
                "email": f"updated-{code.lower()}@example.test",
            }
            updated_response = client.put(
                f"/admin/properties/{property_id}",
                json=update_payload,
                headers=ADMIN_HEADERS,
            )
            inactive_response = client.post(
                f"/admin/properties/{property_id}/status",
                json={"isActive": False},
                headers=ADMIN_HEADERS,
            )
            active_response = client.post(
                f"/admin/properties/{property_id}/status",
                json={"isActive": True},
                headers=ADMIN_HEADERS,
            )

        assert updated_response.status_code == 200, updated_response.text
        updated = updated_response.json()["property"]
        assert updated["name"] == update_payload["name"]
        assert updated["address"] == update_payload["address"]
        assert updated["phone"] == update_payload["phone"]
        assert updated["email"] == update_payload["email"]
        assert updated["timezone"] == update_payload["timezone"]
        assert updated["currency"] == "USD"

        assert inactive_response.status_code == 200, inactive_response.text
        assert inactive_response.json()["property"]["isActive"] is False
        assert active_response.status_code == 200, active_response.text
        assert active_response.json()["property"]["isActive"] is True

        assert _audit_count("property_created", property_id) >= 1
        assert _audit_count("property_updated", property_id) >= 1
        assert _audit_count("property_status_changed", property_id) >= 2
    finally:
        if property_id is not None:
            _delete_property(property_id)


def test_go_live_check_blocks_incomplete_property():
    code = f"QB{uuid4().hex[:6].upper()}"
    property_id = None
    try:
        with TestClient(app) as client:
            created = client.post("/admin/properties", json=_property_payload(code), headers=ADMIN_HEADERS)
            assert created.status_code == 200, created.text
            property_id = created.json()["property"]["id"]

            check = client.get(f"/admin/properties/{property_id}/go-live-check", headers=ADMIN_HEADERS)
            activation = client.post(f"/admin/properties/{property_id}/activate-live", headers=ADMIN_HEADERS)

        assert check.status_code == 200, check.text
        body = check.json()
        assert body["status"] == "red"
        assert body["ready"] is False
        assert "No rooms are configured for this property." in body["blockers"]
        assert activation.status_code == 409
        assert "Property is not ready to go live" in str(activation.json()["detail"])
    finally:
        if property_id is not None:
            _delete_property(property_id)


def test_seed_demo_rooms_for_property_and_room_blocker_clears():
    code = f"QR{uuid4().hex[:6].upper()}"
    property_id = None
    try:
        with TestClient(app) as client:
            created = client.post("/admin/properties", json=_property_payload(code), headers=ADMIN_HEADERS)
            assert created.status_code == 200, created.text
            property_id = created.json()["property"]["id"]

            before = client.get(f"/admin/properties/{property_id}/go-live-check", headers=ADMIN_HEADERS)
            seeded = client.post(f"/admin/properties/{property_id}/seed-demo-rooms", headers=ADMIN_HEADERS)
            rooms = client.get("/rooms/status-board", params={"property_code": code, "date": "2026-06-18"})
            after = client.get(f"/admin/properties/{property_id}/go-live-check", headers=ADMIN_HEADERS)

        assert before.status_code == 200
        assert "No rooms are configured for this property." in before.json()["blockers"]
        assert seeded.status_code == 200, seeded.text
        assert seeded.json()["room_count"] == 5
        assert rooms.status_code == 200, rooms.text
        returned = {(row["room_number"], row["room_type"], row["property_code"]) for row in rooms.json()}
        assert returned == {
            ("101", "Standard Room", code),
            ("102", "Standard Room", code),
            ("201", "Twin Room", code),
            ("202", "Deluxe Room", code),
            ("301", "Suite", code),
        }
        assert after.status_code == 200
        assert "No rooms are configured for this property." not in after.json()["blockers"]
    finally:
        if property_id is not None:
            _delete_property(property_id)


def test_reset_demo_rooms_is_scoped_to_selected_property():
    code = f"QS{uuid4().hex[:6].upper()}"
    other_code = f"QT{uuid4().hex[:6].upper()}"
    property_id = None
    other_property_id = None
    try:
        with TestClient(app) as client:
            created = client.post("/admin/properties", json=_property_payload(code), headers=ADMIN_HEADERS)
            other_created = client.post("/admin/properties", json=_property_payload(other_code), headers=ADMIN_HEADERS)
            assert created.status_code == 200, created.text
            assert other_created.status_code == 200, other_created.text
            property_id = created.json()["property"]["id"]
            other_property_id = other_created.json()["property"]["id"]

            client.post(f"/admin/properties/{property_id}/seed-demo-rooms", headers=ADMIN_HEADERS)
            client.post(f"/admin/properties/{other_property_id}/seed-demo-rooms", headers=ADMIN_HEADERS)
            reset = client.post(f"/admin/properties/{property_id}/reset-demo-rooms", headers=ADMIN_HEADERS)
            rooms = client.get("/rooms/status-board", params={"property_code": code, "date": "2026-06-18"})
            other_rooms = client.get("/rooms/status-board", params={"property_code": other_code, "date": "2026-06-18"})

        assert reset.status_code == 200, reset.text
        assert reset.json()["room_count"] == 5
        assert {row["property_code"] for row in rooms.json()} == {code}
        assert {row["property_code"] for row in other_rooms.json()} == {other_code}
        assert len(rooms.json()) == 5
        assert len(other_rooms.json()) == 5
    finally:
        if property_id is not None:
            _delete_property(property_id)
        if other_property_id is not None:
            _delete_property(other_property_id)


def test_property_authorization_global_scoped_inactive_and_creator_assignment():
    code = f"QU{uuid4().hex[:6].upper()}"
    other_code = f"QV{uuid4().hex[:6].upper()}"
    scoped_email = f"scoped-{code.lower()}@example.test"
    inactive_email = f"inactive-{code.lower()}@example.test"
    assigned_email = f"assigned-{code.lower()}@example.test"
    property_id = None
    other_property_id = None
    try:
        with TestClient(app) as client:
            created = client.post("/admin/properties", json=_property_payload(code), headers=ADMIN_HEADERS)
            other_created = client.post("/admin/properties", json=_property_payload(other_code), headers=ADMIN_HEADERS)
            assert created.status_code == 200, created.text
            assert other_created.status_code == 200, other_created.text
            property_id = created.json()["property"]["id"]
            other_property_id = other_created.json()["property"]["id"]

            assert _assignment_exists("admin@guzo.local", code)

            global_access = client.get(
                "/admin/audit-logs",
                params={"property_code": code},
                headers=ADMIN_HEADERS,
            )

            _create_pms_user(scoped_email, code, role_key="admin")
            scoped_access = client.get(
                "/admin/audit-logs",
                params={"property_code": code},
                headers={"X-PMS-User-Email": scoped_email},
            )
            scoped_cross_property = client.get(
                "/admin/audit-logs",
                params={"property_code": other_code},
                headers={"X-PMS-User-Email": scoped_email},
            )

            _create_pms_user(inactive_email, code, role_key="admin", is_active=False)
            inactive_access = client.get(
                "/admin/audit-logs",
                params={"property_code": code},
                headers={"X-PMS-User-Email": inactive_email},
            )

            _create_pms_user(assigned_email, other_code, role_key="admin")
            assign_response = client.post(
                f"/admin/properties/{property_id}/assign-admin",
                json={"user_email": assigned_email},
                headers=ADMIN_HEADERS,
            )
            assigned_access = client.get(
                "/admin/audit-logs",
                params={"property_code": code},
                headers={"X-PMS-User-Email": assigned_email},
            )

        assert global_access.status_code == 200, global_access.text
        assert scoped_access.status_code == 200, scoped_access.text
        assert scoped_cross_property.status_code == 403
        assert "Your user is not assigned to" in scoped_cross_property.json()["detail"]
        assert inactive_access.status_code == 403
        assert inactive_access.json()["detail"] == "PMS user is inactive or unknown."
        assert assign_response.status_code == 200, assign_response.text
        assert assigned_access.status_code == 200, assigned_access.text
    finally:
        for email in [scoped_email, inactive_email, assigned_email]:
            _delete_user(email)
        if property_id is not None:
            _delete_property(property_id)
        if other_property_id is not None:
            _delete_property(other_property_id)


def test_go_live_check_and_activate_live_when_setup_is_complete():
    code = f"QC{uuid4().hex[:6].upper()}"
    property_id = None
    try:
        with TestClient(app) as client:
            created = client.post("/admin/properties", json=_property_payload(code), headers=ADMIN_HEADERS)
            assert created.status_code == 200, created.text
            property_id = created.json()["property"]["id"]
            _seed_go_live_setup(code)

            check = client.get(f"/admin/properties/{property_id}/go-live-check", headers=ADMIN_HEADERS)
            activation = client.post(f"/admin/properties/{property_id}/activate-live", headers=ADMIN_HEADERS)

        assert check.status_code == 200, check.text
        assert check.json()["status"] == "green"
        assert check.json()["ready"] is True
        assert activation.status_code == 200, activation.text
        activated = activation.json()["property"]
        assert activated["isActive"] is True
        assert activated["onboardingStatus"] == "complete"
        assert _audit_count("property_activated_live", property_id) >= 1
    finally:
        if property_id is not None:
            _delete_property(property_id)


def test_frontend_property_registry_uses_backend_first_with_localstorage_fallback():
    root = Path(__file__).resolve().parents[1]
    context = (root / "guzo_pms_frontend" / "src" / "context" / "PmsContext.tsx").read_text()
    switcher = (root / "guzo_pms_frontend" / "src" / "layout" / "PropertySwitcher.tsx").read_text()
    toolbar = (root / "guzo_pms_frontend" / "src" / "components" / "PmsToolbar.tsx").read_text()
    config = (root / "guzo_pms_frontend" / "src" / "config" / "pms.ts").read_text()

    assert "fetchProperties" in context
    assert "createAdminProperty" in context
    assert "updateAdminProperty" in context
    assert 'const PROPERTY_STORAGE_KEY = "guzo:pms:properties"' in context
    assert "Keep localStorage/demo properties when the backend is unavailable." in context
    assert "propertyOptions.map" in switcher
    assert "propertyOptions.map" in toolbar
    assert 'code: "NN002"' in config
    assert 'name: "N&N Hotel"' in config
