# guzo_backend/db/postgres_bookings.py
#
# Central PostgreSQL connection helper for bookings-related queries.

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def _get_db_params() -> Dict[str, Any]:
    """
    Read DB connection parameters from environment variables.
    """
    return {
        "dbname": os.getenv("GUZO_DB_NAME", "guzo_db"),
        "user": os.getenv("GUZO_DB_USER", "guzo_user"),
        "password": os.getenv("GUZO_DB_PASSWORD", ""),
        "host": os.getenv("GUZO_DB_HOST", "localhost"),
        "port": int(os.getenv("GUZO_DB_PORT", "5432")),
    }


def get_connection():
    """
    Open a standard psycopg2 connection (cursor returns tuples).
    Used for general write/read operations.
    """
    params = _get_db_params()
    logger.debug("Opening PostgreSQL connection for bookings: %r", params)
    conn = psycopg2.connect(**params)
    conn.autocommit = False
    return conn


def get_dict_connection():
    """
    Open a connection whose cursor will return dict-like rows.
    Useful for APIs / JSON responses.
    """
    params = _get_db_params()
    logger.debug("Opening PostgreSQL dict connection for bookings: %r", params)
    conn = psycopg2.connect(cursor_factory=RealDictCursor, **params)
    conn.autocommit = False
    return conn


def test_connection() -> bool:
    """
    Simple health-check helper. Returns True if connection works, else False.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 (we want to log anything)
        logger.error("PostgreSQL bookings connection test failed: %s", exc)
        return False
