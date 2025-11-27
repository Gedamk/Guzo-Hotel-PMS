# guzo_booking_bot/backend_client.py

import os
import requests

GUZO_API_BASE = os.getenv("GUZO_API_BASE", "http://127.0.0.1:8000")


def check_availability_for_bot(
    property_code: str,
    check_in: str,
    check_out: str,
    rooms: int = 1,
) -> dict:
    """
    Call backend /bot/availability endpoint.

    property_code: e.g. "DRE001"
    check_in/check_out: "YYYY-MM-DD"
    rooms: how many rooms guest wants
    """
    url = f"{GUZO_API_BASE}/bot/availability"
    params = {
        "hotel": property_code,
        "in": check_in,
        "out": check_out,
        "rooms": rooms,
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
