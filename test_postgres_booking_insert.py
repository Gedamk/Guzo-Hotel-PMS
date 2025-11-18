# -*- coding: utf-8 -*-
"""
Quick manual test: insert one booking into Postgres.
Run with:
    source venv/Scripts/activate
    python test_postgres_booking_insert.py
"""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv  # make sure python-dotenv is installed
from guzo_backend.modules.postgres_bookings import save_booking_to_postgres


# ------------------------------------------------
# Load .env from project root (C:/Users/Gedan/Desktop/Guzo/.env)
# ------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

# Optional: quick sanity check
if not os.getenv("GUZO_DB_PASSWORD"):
    raise RuntimeError("GUZO_DB_PASSWORD is still not set after load_dotenv()")


def main():
    # ⚠️ CHANGE THIS: use a real property_code from your hotels table / sheet
    sample_booking = {
    "confirmation_id": "TEST-GUZO-001",
    "property_code": "DRE001",  # ← replace with real value from SELECT
    "guest_name": "Test Guest",
    "guest_email": "test.guest@example.com",
    "check_in_date": date.today(),
    "check_out_date": date.today(),
    "nights": 1,
    "room_type": "Standard Room",
    "rate_per_night_etb": 1500,
    "total_revenue_etb": 1500,
    "payment_method": "Cash",
    "booking_status": "Confirmed",
    "payment_status": "Pending",
}

    new_id = save_booking_to_postgres(sample_booking)
    print("Inserted / updated booking with id:", new_id)


if __name__ == "__main__":
    main()
