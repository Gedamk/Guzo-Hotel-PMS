from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_auth_service import decode_access_token
from guzo_backend.services.pms_security_service import require_property_access


router = APIRouter(prefix="/search", tags=["global-search"])


class GlobalSearchResult(BaseModel):
    id: str
    module: str
    title: str
    subtitle: str
    status: str | None = None
    target_route: str
    record_type: str
    record_id: str


class GlobalSearchGroup(BaseModel):
    key: str
    label: str
    results: list[GlobalSearchResult]


class GlobalSearchResponse(BaseModel):
    query: str
    groups: list[GlobalSearchGroup]


def _require_search_user(
    authorization: str | None = Header(None),
    x_pms_user_email: str | None = Header(None),
) -> dict[str, Any]:
    if authorization and authorization.lower().startswith("bearer "):
        claims = decode_access_token(authorization.split(" ", 1)[1].strip())
        return {
            "email": claims.get("email") or claims.get("sub") or "pms-user@guzo.local",
            "property_code": claims.get("property_code"),
            "role_key": claims.get("role_key"),
        }
    if x_pms_user_email:
        return {"email": x_pms_user_email, "property_code": None, "role_key": "dev"}
    raise HTTPException(status_code=401, detail="Authentication is required for PMS global search.")


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return bool(
            db.execute(
                text(
                    """
                    SELECT EXISTS (
                      SELECT 1
                      FROM information_schema.tables
                      WHERE table_name = :table_name
                    )
                    """
                ),
                {"table_name": table_name},
            ).scalar()
        )
    except SQLAlchemyError:
        return False


def _table_columns(db: Session, table_name: str) -> set[str]:
    if not _table_exists(db, table_name):
        return set()
    try:
        rows = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalars()
        return {str(row) for row in rows}
    except SQLAlchemyError:
        return set()


def _column(columns: set[str], name: str, fallback: str = "NULL") -> str:
    return name if name in columns else fallback


def _where_like(columns: set[str], candidates: list[str]) -> str:
    searchable = [column for column in candidates if column in columns]
    if not searchable:
        return "FALSE"
    return " OR ".join(f"CAST({column} AS TEXT) ILIKE :pattern" for column in searchable)


def _property_filter(columns: set[str]) -> str:
    return "AND property_code = :property_code" if "property_code" in columns else "AND FALSE"


def _result(
    *,
    module: str,
    record_type: str,
    record_id: Any,
    title: str | None,
    subtitle: str | None,
    status: str | None,
    target_route: str,
) -> GlobalSearchResult:
    result_id = f"{record_type}:{record_id}"
    return GlobalSearchResult(
        id=result_id,
        module=module,
        title=title or f"{record_type.title()} {record_id}",
        subtitle=subtitle or "",
        status=status,
        target_route=target_route,
        record_type=record_type,
        record_id=str(record_id),
    )


def _search_bookings(db: Session, property_code: str, pattern: str) -> tuple[list[GlobalSearchResult], list[GlobalSearchResult]]:
    columns = _table_columns(db, "bookings")
    if not columns:
        return [], []
    where = _where_like(
        columns,
        ["confirmation_id", "guest_name", "guest_phone", "guest_email", "room_number", "id"],
    )
    rows = db.execute(
        text(
            f"""
            SELECT id,
                   {_column(columns, "confirmation_id")} AS confirmation_id,
                   {_column(columns, "guest_name", "''")} AS guest_name,
                   {_column(columns, "guest_phone")} AS guest_phone,
                   {_column(columns, "guest_email")} AS guest_email,
                   {_column(columns, "room_number")} AS room_number,
                   {_column(columns, "booking_status", "''")} AS booking_status,
                   {_column(columns, "check_in_date")} AS check_in_date,
                   {_column(columns, "check_out_date")} AS check_out_date
            FROM bookings
            WHERE 1 = 1
              {_property_filter(columns)}
              AND ({where})
            ORDER BY id DESC
            LIMIT 10
            """
        ),
        {"property_code": property_code, "pattern": pattern},
    ).mappings().all()
    reservations: list[GlobalSearchResult] = []
    guests: list[GlobalSearchResult] = []
    seen_guests: set[str] = set()
    for row in rows:
        stay = f"{row.get('check_in_date') or '-'} to {row.get('check_out_date') or '-'}"
        room = f"Room {row.get('room_number')}" if row.get("room_number") else "Room TBD"
        reservations.append(
            _result(
                module="Reservations",
                record_type="booking",
                record_id=row["id"],
                title=f"{row.get('confirmation_id') or '#'+str(row['id'])} | {row.get('guest_name') or 'Guest'}",
                subtitle=f"{stay} | {room}",
                status=row.get("booking_status"),
                target_route="/reservations",
            )
        )
        guest_key = str(row.get("guest_name") or "").lower()
        if guest_key and guest_key not in seen_guests:
            seen_guests.add(guest_key)
            guests.append(
                _result(
                    module="Guests",
                    record_type="guest",
                    record_id=row["id"],
                    title=row.get("guest_name") or "Guest",
                    subtitle=f"{row.get('guest_phone') or row.get('guest_email') or stay}",
                    status=row.get("booking_status"),
                    target_route=f"/guest-profiles?guest={row.get('guest_name') or ''}",
                )
            )
    return reservations, guests


def _search_rooms(db: Session, property_code: str, pattern: str) -> list[GlobalSearchResult]:
    columns = _table_columns(db, "rooms")
    if not columns:
        return []
    where = _where_like(columns, ["room_number", "room_type", "hk_status", "status", "maintenance_note"])
    rows = db.execute(
        text(
            f"""
            SELECT {_column(columns, "id", "room_number")} AS id,
                   {_column(columns, "room_number", "''")} AS room_number,
                   {_column(columns, "room_type", "''")} AS room_type,
                   COALESCE({_column(columns, "hk_status")}, {_column(columns, "status")}, '') AS room_status
            FROM rooms
            WHERE 1 = 1
              {_property_filter(columns)}
              AND ({where})
            ORDER BY room_number
            LIMIT 10
            """
        ),
        {"property_code": property_code, "pattern": pattern},
    ).mappings().all()
    return [
        _result(
            module="Rooms",
            record_type="room",
            record_id=row.get("id") or row.get("room_number"),
            title=f"Room {row.get('room_number')}",
            subtitle=row.get("room_type") or "Room status board",
            status=row.get("room_status"),
            target_route="/housekeeping",
        )
        for row in rows
    ]


def _search_folios(db: Session, property_code: str, pattern: str) -> list[GlobalSearchResult]:
    columns = _table_columns(db, "folios")
    if not columns:
        return []
    where = _where_like(columns, ["id", "folio_number", "booking_id", "guest_name", "status"])
    rows = db.execute(
        text(
            f"""
            SELECT id,
                   {_column(columns, "folio_number")} AS folio_number,
                   {_column(columns, "booking_id")} AS booking_id,
                   {_column(columns, "guest_name", "''")} AS guest_name,
                   {_column(columns, "balance", "0")} AS balance,
                   {_column(columns, "status", "''")} AS status
            FROM folios
            WHERE 1 = 1
              {_property_filter(columns)}
              AND ({where})
            ORDER BY id DESC
            LIMIT 10
            """
        ),
        {"property_code": property_code, "pattern": pattern},
    ).mappings().all()
    return [
        _result(
            module="Folios",
            record_type="folio",
            record_id=row["id"],
            title=f"Folio {row.get('folio_number') or row['id']}",
            subtitle=f"{row.get('guest_name') or 'Guest'} | Balance ETB {float(row.get('balance') or 0):,.0f}",
            status=row.get("status"),
            target_route="/finance",
        )
        for row in rows
    ]


def _search_public_requests(db: Session, property_code: str, pattern: str) -> list[GlobalSearchResult]:
    columns = _table_columns(db, "public_booking_requests")
    if not columns:
        return []
    where = _where_like(columns, ["id", "guest_name", "guest_phone", "guest_email", "room_type", "booking_status"])
    rows = db.execute(
        text(
            f"""
            SELECT id,
                   {_column(columns, "guest_name", "''")} AS guest_name,
                   {_column(columns, "guest_phone")} AS guest_phone,
                   {_column(columns, "guest_email")} AS guest_email,
                   {_column(columns, "room_type")} AS room_type,
                   {_column(columns, "booking_status", "''")} AS booking_status,
                   {_column(columns, "check_in_date")} AS check_in_date,
                   {_column(columns, "check_out_date")} AS check_out_date
            FROM public_booking_requests
            WHERE 1 = 1
              {_property_filter(columns)}
              AND ({where})
            ORDER BY id DESC
            LIMIT 10
            """
        ),
        {"property_code": property_code, "pattern": pattern},
    ).mappings().all()
    return [
        _result(
            module="Booking Hub",
            record_type="public_request",
            record_id=row["id"],
            title=f"Request #{row['id']} | {row.get('guest_name') or 'Guest'}",
            subtitle=f"{row.get('room_type') or 'Room TBD'} | {row.get('check_in_date') or '-'} to {row.get('check_out_date') or '-'}",
            status=row.get("booking_status"),
            target_route="/booking-hub",
        )
        for row in rows
    ]


def _search_notifications(db: Session, property_code: str, pattern: str) -> list[GlobalSearchResult]:
    columns = _table_columns(db, "guest_notification_outbox")
    if not columns:
        return []
    where = _where_like(columns, ["id", "recipient", "message", "status", "booking_id", "public_request_id"])
    rows = db.execute(
        text(
            f"""
            SELECT id,
                   {_column(columns, "recipient", "''")} AS recipient,
                   {_column(columns, "action", "''")} AS action,
                   {_column(columns, "message", "''")} AS message,
                   {_column(columns, "status", "''")} AS status
            FROM guest_notification_outbox
            WHERE 1 = 1
              {_property_filter(columns)}
              AND ({where})
            ORDER BY id DESC
            LIMIT 10
            """
        ),
        {"property_code": property_code, "pattern": pattern},
    ).mappings().all()
    return [
        _result(
            module="Notifications",
            record_type="notification",
            record_id=row["id"],
            title=f"Notification #{row['id']} | {row.get('recipient') or 'Guest'}",
            subtitle=row.get("action") or (row.get("message") or "")[:80],
            status=row.get("status"),
            target_route="/coming-soon?feature=Notifications",
        )
        for row in rows
    ]


@router.get("/global", response_model=GlobalSearchResponse)
def global_search(
    q: str = Query("", description="Search text"),
    property_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(_require_search_user),
):
    query = q.strip()
    normalized_property = property_code.strip().upper()
    require_property_access(db, property_code=normalized_property, user_email=user.get("email"))
    if len(query) < 2:
        return GlobalSearchResponse(
            query=query,
            groups=[
                GlobalSearchGroup(key="reservations", label="Reservations / Bookings", results=[]),
                GlobalSearchGroup(key="guests", label="Guests", results=[]),
                GlobalSearchGroup(key="rooms", label="Rooms", results=[]),
                GlobalSearchGroup(key="folios", label="Folios", results=[]),
                GlobalSearchGroup(key="booking_hub", label="Booking Hub Public Requests", results=[]),
                GlobalSearchGroup(key="notifications", label="Notifications", results=[]),
            ],
        )

    pattern = f"%{query}%"
    reservations, guests = _search_bookings(db, normalized_property, pattern)
    groups = [
        GlobalSearchGroup(key="reservations", label="Reservations / Bookings", results=reservations),
        GlobalSearchGroup(key="guests", label="Guests", results=guests),
        GlobalSearchGroup(key="rooms", label="Rooms", results=_search_rooms(db, normalized_property, pattern)),
        GlobalSearchGroup(key="folios", label="Folios", results=_search_folios(db, normalized_property, pattern)),
        GlobalSearchGroup(
            key="booking_hub",
            label="Booking Hub Public Requests",
            results=_search_public_requests(db, normalized_property, pattern),
        ),
        GlobalSearchGroup(key="notifications", label="Notifications", results=_search_notifications(db, normalized_property, pattern)),
    ]
    return GlobalSearchResponse(query=query, groups=groups)
