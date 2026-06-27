# guzo_booking_bot/modules/backend_client.py
#
# Helper functions for the Telegram bot to talk to the Guzo backend
# (FastAPI running at http://127.0.0.1:8000).

import os
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("GuzoBotBackendClient")

API_BASE = os.getenv("GUZO_API_BASE", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("GUZO_API_TOKEN", "")


def _auth_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    return headers


def check_availability_for_bot(
    property_code: str,
    check_in: str,
    check_out: str,
    rooms: int = 1,
) -> Dict[str, Any]:
    """
    Call /bot/availability from the bot side.

    Returns the JSON dict from backend, e.g.:
    {
      "property_code": "DRE001",
      "check_in": "2025-12-01",
      "check_out": "2025-12-03",
      "requested_rooms": 1,
      "total_rooms": 2,
      "overlapping_bookings": 0,
      "available_rooms": 2,
      "available": true,
      "message": "Yes, 2 room(s) available at DRE001 from 2025-12-01 to 2025-12-03."
    }
    """
    url = f"{API_BASE}/bot/availability"
    params = {
        "property_code": property_code,
        "check_in": check_in,
        "check_out": check_out,
        "rooms": rooms,
    }

    logger.info("Calling %s with params=%r", url, params)

    resp = requests.get(url, headers=_auth_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Availability response: %r", data)
    return data


def create_booking_for_bot(
    property_code: str,
    check_in: str,
    check_out: str,
    guest_name: str,
    channel: str = "telegram",
    total_amount_etb: Optional[float] = None,
    room_type: Optional[str] = None,
    guest_email: Optional[str] = None,
    guest_count: Optional[int] = None,
    payment_method: Optional[str] = None,
    payment_status: Optional[str] = None,
    guest_phone: Optional[str] = None,
    adults: Optional[int] = None,
    children: Optional[int] = None,
    purpose_of_visit: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call /bot/bookings to create a booking from the bot.

    Expects backend /bot/bookings to return JSON like:
    {
      "booking_id": 123,
      "property_code": "DRE001",
      "check_in": "...",
      "check_out": "...",
      "guest_name": "...",
      "channel": "telegram",
      ...
    }
    """
    url = f"{API_BASE}/bot/bookings"
    payload: Dict[str, Any] = {
        "property_code": property_code,
        "check_in": check_in,
        "check_out": check_out,
        "guest_name": guest_name,
        "channel": channel,
    }

    if total_amount_etb is not None:
        payload["total_amount_etb"] = total_amount_etb
    if room_type:
        payload["room_type"] = room_type
    if guest_email:
        payload["guest_email"] = guest_email
    if guest_count is not None:
        payload["guest_count"] = guest_count
    if payment_method:
        payload["payment_method"] = payment_method
    if payment_status:
        payload["payment_status"] = payment_status
    if guest_phone:
        payload["guest_phone"] = guest_phone
    if adults is not None:
        payload["adults"] = adults
    if children is not None:
        payload["children"] = children
    if purpose_of_visit:
        payload["purpose_of_visit"] = purpose_of_visit
    if notes:
        payload["notes"] = notes

    logger.info("Calling %s with json=%r", url, payload)

    resp = requests.post(url, headers=_auth_headers(), json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Create-booking response: %r", data)
    return data
