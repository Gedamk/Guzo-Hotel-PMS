# guzo_backend/core/postgres_bookings.py
#
# Single source of truth for PostgreSQL connections in Guzo backend.

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.

    GUZO_DB_NAME (default: guzo_db)
    GUZO_DB_USER (default: guzo_user)
    GUZO_DB_PASSWORD (required)
    GUZO_DB_HOST (default: localhost)
    GUZO_DB_PORT (default: 5432)
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        logger.error("GUZO_DB_PASSWORD is not set; cannot connect to DB.")
        raise RuntimeError(
            "Database connection helper (postgres_bookings.get_connection) is not configured."
        )

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )


def dict_cursor(conn) -> Any:
    """
    Convenience helper for a RealDictCursor context.
    Example:
        with dict_cursor(get_connection()) as cur:
            cur.execute("SELECT 1 AS x")
            row = cur.fetchone()
    """
    return conn.cursor(cursor_factory=RealDictCursor)
