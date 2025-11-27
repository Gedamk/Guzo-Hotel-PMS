# guzo_backend/db/postgres_payments.py

import logging
from typing import Optional
from datetime import datetime

from psycopg2.extras import RealDictCursor

from .postgres_rooms import get_connection  # reuse your connection helper

logger = logging.getLogger(__name__)


def create_payment(
    booking_id: int,
    property_code: str,
    provider: str,
    amount_etb: float,
    currency: str = "ETB",
    status: str = "success",
    external_ref: Optional[str] = None,
) -> int:
    """
    Insert a payment row linked to a booking.

    For now we assume offline success:
    - provider can be 'cash', 'card', 'bank'
    - status = 'success'
    Later we can call gateways (Chapa/Telebirr/Stripe) and update status.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO payments (
                        booking_id,
                        property_code,
                        provider,
                        status,
                        amount_etb,
                        currency,
                        external_ref,
                        paid_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id;
                    """,
                    (
                        booking_id,
                        property_code,
                        provider,
                        status,
                        amount_etb,
                        currency,
                        external_ref,
                    ),
                )
                row = cur.fetchone()
                payment_id = row["id"]
                logger.info(
                    "[Payments] Created %s payment id=%s for booking_id=%s amount=%s %s",
                    provider,
                    payment_id,
                    booking_id,
                    amount_etb,
                    currency,
                )
                return payment_id
    finally:
        conn.close()
