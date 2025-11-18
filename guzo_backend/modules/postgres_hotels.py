# -*- coding: utf-8 -*-
"""
postgres_hotels.py
--------------------
Helpers to read hotel data from PostgreSQL for Guzo Guest Assist.
"""

import os
import logging

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


def get_pg_connection():
    """Create a PostgreSQL connection using env variables."""
    load_dotenv()

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "guzo_db")
    user = os.getenv("DB_USER", "guzo_user")
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise RuntimeError("DB_PASSWORD is not set in .env")

    logger.info(
        "Connecting to PostgreSQL %s as %s@%s:%s",
        name,
        user,
        host,
        port,
    )

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
    )
    return conn


def get_hotel_by_property_code(property_code: str):
    """
    Look up one hotel row by property_code from PostgreSQL.
    Returns a dict or None.
    """
    if not property_code:
        return None

    property_code = str(property_code).strip().upper()

    conn = get_pg_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    property_code,
                    name,
                    city,
                    email,
                    phone,
                    telegram_chat_id,
                    sheet_id,
                    created_at
                FROM hotels
                WHERE UPPER(property_code) = %s
                """,
                (property_code,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning(
                    "[PostgresHotels] No hotel found for property_code=%s",
                    property_code,
                )
                return None

            logger.info(
                "[PostgresHotels] Resolved hotel from Postgres: %s (%s)",
                row["name"],
                row["property_code"],
            )
            return dict(row)
    finally:
        conn.close()
