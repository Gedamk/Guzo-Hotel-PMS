# guzo_backend/dependencies.py
#
# Shared FastAPI dependencies:
#   - get_db_connection()  → PostgreSQL connection using GUZO_DB_* env vars
#   - get_db()             → SQLAlchemy Session (for ORM-style access)
#   - verify_admin_token() → protects admin/API endpoints
#
# Used by:
#   - guzo_backend.api.bookings_list_api
#   - guzo_backend.api.frontdesk_walkin_api
#   - guzo_backend.api.frontdesk_assign_api
#   - (and can be reused in other routers)

from __future__ import annotations

import logging
import os
from typing import Optional, Generator

import psycopg2
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from .core.postgres_db import SessionLocal

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Raw psycopg2 database connection helper
# ------------------------------------------------------------


def get_db_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.

    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                ...
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        logger.warning("GUZO_DB_PASSWORD is not set; connection may fail.")

    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
        )
        return conn
    except Exception as exc:
        logger.error("Error connecting to PostgreSQL: %s", exc)
        # Surface as HTTP 500 when used inside request handlers
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {exc}",
        ) from exc


# ------------------------------------------------------------
# SQLAlchemy Session dependency (ORM-style)
# ------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy Session.

    Used by:
      - frontdesk_walkin_api
      - frontdesk_assign_api
      - any other ORM-based endpoints

    Example in a router:

        from fastapi import Depends, APIRouter
        from sqlalchemy.orm import Session
        from guzo_backend.dependencies import get_db

        router = APIRouter()

        @router.get("/something")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------
# Admin token verification
# ------------------------------------------------------------


def _extract_token(
    x_admin_token: Optional[str],
    authorization: Optional[str],
) -> Optional[str]:
    """
    Decide which header to use as the admin token.

    Priority:
      1. X-Admin-Token: <token>
      2. Authorization: Bearer <token>
      3. Authorization: <token>
    """
    if x_admin_token:
        return x_admin_token

    if authorization:
        lower = authorization.lower()
        if lower.startswith("bearer "):
            return authorization[7:].strip()
        return authorization.strip()

    return None


def verify_admin_token(
    x_admin_token: Optional[str] = Header(
        default=None,
        alias="X-Admin-Token",
        description="Optional admin token header.",
    ),
    authorization: Optional[str] = Header(
        default=None,
        alias="Authorization",
        description="Optional Authorization: Bearer <token> header.",
    ),
) -> None:
    """
    FastAPI dependency to protect admin endpoints.

    In your frontend, you are calling APIs with:
        Authorization: Bearer admin-secret-123

    This function compares that to ADMIN_API_TOKEN env var
    (or falls back to 'admin-secret-123' if not set).
    """
    expected = os.getenv("ADMIN_API_TOKEN", "admin-secret-123")

    token = _extract_token(x_admin_token, authorization)

    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )

    # If token is valid, just return None; FastAPI sees dependency as satisfied.
    return None
