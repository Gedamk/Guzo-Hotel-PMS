"""
Simplified PostgreSQL / SQLAlchemy configuration for local Guzo development.

- Uses a single fixed user/database/host/port.
- You only need to put your REAL `guzo_user` password in ONE place.
- Exposes:
    - `engine`        -> for raw SQL (text queries, etc.)
    - `SessionLocal`  -> for ORM sessions
    - `get_db()`      -> FastAPI dependency (yielding Session)
    - `get_db_connection()` -> context manager for old-style raw connections
"""

from contextlib import contextmanager
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

# -------------------------------------------------------------------
# 🔐 LOCAL DATABASE SETTINGS
# -------------------------------------------------------------------
# These should match what you already use in psql:
#
#   psql "postgresql://guzo_user@localhost:5432/guzo_db"
#   Password for user guzo_user:  <--- THAT password goes below
#
DB_USER = os.getenv("GUZO_DB_USER") or os.getenv("POSTGRES_USER", "guzo_user")
DB_NAME = os.getenv("GUZO_DB_NAME") or os.getenv("POSTGRES_DB", "guzo_db")
DB_HOST = os.getenv("GUZO_DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("GUZO_DB_PORT") or os.getenv("POSTGRES_PORT", "5432"))

# ⛔ IMPORTANT:
# This MUST be the same password you type when psql prompts:
#   Password for user guzo_user:
DB_PASSWORD = os.getenv("GUZO_DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")


# -------------------------------------------------------------------
# Build SQLAlchemy URL
# -------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# Engine with basic health-checking
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

# Session factory used by FastAPI
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# -------------------------------------------------------------------
# FastAPI dependency (ORM session)
# -------------------------------------------------------------------
def get_db() -> Generator:
    """
    FastAPI dependency that yields a SQLAlchemy session.

    Usage in routes:
        from guzo_backend.core.postgres_db import get_db
        from sqlalchemy.orm import Session

        @router.get("/something")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# Backwards-compatible raw connection helper
# -------------------------------------------------------------------
@contextmanager
def get_db_connection():
    """
    Backwards-compatible helper for old routers that expect
    `get_db_connection()` as a context manager:

        from ..core.postgres_db import get_db_connection

        with get_db_connection() as conn:
            rows = conn.execute(...)

    Internally this just uses the same SQLAlchemy engine.
    """
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()
