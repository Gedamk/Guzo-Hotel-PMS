# mini_debug_app.py

from typing import List

from fastapi import FastAPI
from sqlalchemy import text

from guzo_backend.core.postgres_db import engine

app = FastAPI(
    title="Guzo Mini Debug App",
    version="1.0.0",
)


@app.get("/debug/bookings_raw", tags=["debug"])
def bookings_raw() -> List[dict] | dict:
    """
    Return a raw dump of bookings (no filters).

    If something goes wrong, return the error message so we can see
    exactly what is failing.
    """
    sql = """
        SELECT
            id,
            confirmation_id,
            guest_name,
            check_in_date,
            check_out_date,
            booking_status,
            property_code
        FROM bookings
        ORDER BY id
        LIMIT 50;
    """
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(sql)).fetchall()
        # Convert rows to list of dicts
        return [dict(r._mapping) for r in rows]
    except Exception as exc:
        # Print full traceback to the server console
        import traceback

        traceback.print_exc()
        # Return error message to the client
        return {"error": str(exc)}
