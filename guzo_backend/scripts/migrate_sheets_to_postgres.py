# -*- coding: utf-8 -*-
"""
migrate_sheets_to_postgres.py
---------------------------------
One-time (or repeatable) migration from Google Sheets -> PostgreSQL.

- Reads hotels from Hotel_Contacts_Master / JSON
- Inserts / updates rows in PostgreSQL "hotels" table.
"""

import os
import logging

from dotenv import load_dotenv
import psycopg2

from guzo_backend.modules import google_sheets

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def get_pg_connection():
    """Create a PostgreSQL connection using env variables."""
    load_dotenv()  # load from project .env

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "guzo_db")
    user = os.getenv("DB_USER", "guzo_user")
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise RuntimeError("DB_PASSWORD is not set in .env")

    logging.info(f"Connecting to PostgreSQL {name} as {user}@{host}:{port}")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
    )
    conn.autocommit = False
    return conn


def normalize_hotel_row(h):
    """
    Map one hotel row from Google Sheets / JSON to our DB columns.
    Adjust keys to match your actual sheet headers.
    """

    def s(value):
        """Safe string: handle None, numbers, etc."""
        if value is None:
            return ""
        return str(value)

    property_code_raw = (
        h.get("Property Code")
        or h.get("property_code")
        or h.get("PROPERTY_CODE")
        or ""
    )

    name_raw = (
        h.get("Hotel Name")
        or h.get("name")
        or h.get("HOTEL_NAME")
        or ""
    )

    city_raw = h.get("City") or h.get("city") or ""
    email_raw = h.get("Reservation Email") or h.get("email") or ""
    phone_raw = h.get("Phone") or h.get("phone") or ""
    telegram_chat_id_raw = (
        h.get("Telegram Chat ID")
        or h.get("telegram_chat_id")
        or ""
    )
    sheet_id_raw = h.get("Sheet ID") or h.get("sheet_id") or ""

    return {
        "property_code": s(property_code_raw).strip().upper(),
        "name": s(name_raw).strip(),
        "city": s(city_raw).strip(),
        "email": s(email_raw).strip(),
        "phone": s(phone_raw).strip(),
        "telegram_chat_id": s(telegram_chat_id_raw).strip(),
        "sheet_id": s(sheet_id_raw).strip(),
    }


def migrate_hotels():
    logging.info("Loading hotels from Google Sheets / JSON...")
    hotels = google_sheets.read_hotels_master()

    # ��� Handle DataFrame OR list
    if hotels is None:
        logging.warning("No hotels returned (None). Stopping.")
        return

    # If it's a pandas DataFrame, use .empty and convert to records
    if hasattr(hotels, "empty"):
        if hotels.empty:
            logging.warning("Hotels DataFrame is empty. Stopping.")
            return
        records = hotels.to_dict(orient="records")
    else:
        # Assume it's already a list
        if not hotels:
            logging.warning("Hotels list is empty. Stopping.")
            return
        records = hotels

    logging.info(f"Found {len(records)} hotels in master source.")

    conn = get_pg_connection()
    cur = conn.cursor()

    sql = """
    INSERT INTO hotels (
        property_code, name, city, email, phone, telegram_chat_id, sheet_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (property_code) DO UPDATE SET
        name = EXCLUDED.name,
        city = EXCLUDED.city,
        email = EXCLUDED.email,
        phone = EXCLUDED.phone,
        telegram_chat_id = EXCLUDED.telegram_chat_id,
        sheet_id = EXCLUDED.sheet_id;
    """

    count = 0
    for raw in records:
        row = normalize_hotel_row(raw)

        if not row["property_code"] or not row["name"]:
            logging.warning(f"Skipping row with missing property_code or name: {raw}")
            continue

        cur.execute(
            sql,
            (
                row["property_code"],
                row["name"],
                row["city"],
                row["email"],
                row["phone"],
                row["telegram_chat_id"],
                row["sheet_id"],
            ),
        )
        count += 1

    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"✅ Migration finished. Inserted/updated {count} hotel rows.")


if __name__ == "__main__":
    migrate_hotels()
