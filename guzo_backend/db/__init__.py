"""
guzo_backend.db – central PostgreSQL connection helper for Guzo Guest Assist.
"""

import os
import logging

import psycopg2

logger = logging.getLogger(__name__)


def get_connection():
    """
    Open a new PostgreSQL connection using GUZO_DB_* env vars.

    Make sure these are set in your .env:

      GUZO_DB_NAME=guzo_db
      GUZO_DB_USER=guzo_user
      GUZO_DB_PASSWORD=your_password_here
      GUZO_DB_HOST=localhost
      GUZO_DB_PORT=5432
    """
    dbname = os.getenv("GUZO_DB_NAME", "guzo_db")
    user = os.getenv("GUZO_DB_USER", "guzo_user")
    password = os.getenv("GUZO_DB_PASSWORD")
    host = os.getenv("GUZO_DB_HOST", "localhost")
    port = os.getenv("GUZO_DB_PORT", "5432")

    if not password:
        raise RuntimeError("GUZO_DB_PASSWORD is not set in environment")

    logger.info("Connecting to PostgreSQL %s as %s@%s:%s", dbname, user, host, port)

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
