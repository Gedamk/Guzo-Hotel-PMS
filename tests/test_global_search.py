from fastapi import FastAPI
from fastapi.testclient import TestClient

from guzo_backend.api import search_api
from guzo_backend.api.search_api import router
from guzo_backend.dependencies import get_db


def _fake_db():
    yield object()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def test_global_search_requires_authentication():
    response = _client().get("/search/global", params={"q": "guest"})

    assert response.status_code == 401


def test_global_search_empty_query_returns_safe_groups(monkeypatch):
    monkeypatch.setattr(search_api, "require_property_access", lambda *args, **kwargs: {"email": "admin@guzo.local"})
    response = _client().get(
        "/search/global",
        params={"q": " ", "property_code": "DRE001"},
        headers={"X-PMS-User-Email": "admin@guzo.local"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == ""
    assert [group["key"] for group in payload["groups"]] == [
        "reservations",
        "guests",
        "rooms",
        "folios",
        "booking_hub",
        "notifications",
    ]
    assert all(group["results"] == [] for group in payload["groups"])
