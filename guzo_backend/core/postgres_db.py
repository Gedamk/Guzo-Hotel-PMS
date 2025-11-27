# guzo_backend/core/postgres_db.py
#
# Shared PostgreSQL connection helper for all modules.
# Uses GUZO_DB_* environment variables.

from __future__ import annotations

import os
import logging

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as exc:
        logger.exception(
            "❌ Failed to open PostgreSQL connection to %s@%s:%s/%s",
            user,
            host,
            port,
            dbname,
        )
        raise
