# guzo_db/core.py
"""
Central Postgres connection helper for Guzo Guest Assist.

Any module that needs a DB connection should import:
    from guzo_db.core import get_connection
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """
    Open a new psycopg2 connection using env vars.

    Expected env vars (already used elsewhere in your project):
      - POSTGRES_HOST
      - POSTGRES_PORT
      - POSTGRES_DB
      - POSTGRES_USER
      - POSTGRES_PASSWORD
    """
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "guzo_db")
    user = os.getenv("POSTGRES_USER", "guzo_user")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")

    conn = psycopg2.connect(
      host=host,
      port=port,
      dbname=dbname,
      user=user,
      password=password,
      cursor_factory=RealDictCursor,
    )
    return conn
