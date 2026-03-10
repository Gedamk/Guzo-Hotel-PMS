from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from guzo_backend.core.postgres_db import get_db_connection

router = APIRouter(tags=["finance"])


class FolioLine(BaseModel):
    id: Optional[str] = None
    date: Optional[str] = None
    description: str
    amount: float
    currency: str = "ETB"
    kind: str  # "charge" | "payment"
    category_or_method: str  # category for charge, method for payment


class FolioSummary(BaseModel):
    balance: float
    currency: str = "ETB"
    lines: List[FolioLine] = Field(default_factory=list)


@router.get("/finance/folio/summary", response_model=FolioSummary)
def finance_folio_summary(
    business_date: date = Query(..., description="YYYY-MM-DD"),
    property_code: str = Query(..., min_length=3),
    booking_id: Optional[int] = Query(None),
):
    """
    DB-backed folio summary using folios + folio_transactions.

    - If booking_id is provided:
      returns detailed folio lines and live balance for that booking.
    - If booking_id is omitted:
      returns property/day totals (balance only) with empty lines.

    Never 500s: returns safe empty response on unexpected error.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:

                # -------------------------
                # Detailed folio (booking)
                # -------------------------
                if booking_id is not None:
                    cur.execute(
                        """
                        SELECT
                            id,
                            COALESCE(currency, 'ETB') AS currency,
                            COALESCE(balance, 0)::float8 AS balance
                        FROM folios
                        WHERE property_code = %s
                          AND booking_id = %s
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (property_code, booking_id),
                    )
                    folio_row = cur.fetchone()

                    if not folio_row:
                        return FolioSummary(balance=0.0, currency="ETB", lines=[])

                    folio_id = int(folio_row[0])
                    currency = folio_row[1] or "ETB"
                    balance = float(folio_row[2] or 0.0)

                    cur.execute(
                        """
                        SELECT
                            id::text AS id,
                            business_date::text AS date,
                            COALESCE(description, '') AS description,
                            amount::float8 AS amount,
                            COALESCE(currency, 'ETB') AS currency,
                            txn_type AS kind,
                            COALESCE(category, '') AS category_or_method
                        FROM folio_transactions
                        WHERE folio_id = %s
                        ORDER BY business_date ASC, id ASC
                        """,
                        (folio_id,),
                    )
                    rows = cur.fetchall()

                    lines: List[FolioLine] = []
                    for r in rows:
                        lines.append(
                            FolioLine(
                                id=r[0],
                                date=r[1],
                                description=r[2] or "",
                                amount=float(r[3] or 0.0),
                                currency=r[4] or "ETB",
                                kind=r[5],
                                category_or_method=r[6] or "",
                            )
                        )

                    return FolioSummary(
                        balance=balance,
                        currency=currency,
                        lines=lines,
                    )

                # -------------------------
                # Property/day totals
                # -------------------------
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN txn_type = 'charge' THEN amount ELSE 0 END), 0)::float8 AS total_charges,
                        COALESCE(SUM(CASE WHEN txn_type = 'payment' THEN amount ELSE 0 END), 0)::float8 AS total_payments
                    FROM folio_transactions
                    WHERE property_code = %s
                      AND business_date = %s
                    """,
                    (property_code, business_date),
                )
                totals = cur.fetchone()
                charges_total = float(totals[0] or 0.0)
                payments_total = float(totals[1] or 0.0)

                return FolioSummary(
                    balance=(charges_total - payments_total),
                    currency="ETB",
                    lines=[],
                )

    except Exception:
        return FolioSummary(balance=0.0, currency="ETB", lines=[])