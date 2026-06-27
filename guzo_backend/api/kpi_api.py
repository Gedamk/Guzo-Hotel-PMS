from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.db.postgres_bookings import get_connection
from guzo_backend.core.booking_status import ACTIVE_STATUSES
from guzo_backend.services.pms_security_service import require_property_access

router = APIRouter(prefix="/kpi", tags=["kpi"])


class DailyKpiOut(BaseModel):
    property_code: str
    date: date
    adr: float
    revpar: float
    rooms_sold: int
    revenue_total: float


def compute_daily_kpi(property_code: str, target: date) -> DailyKpiOut:
    """
    Compute ADR / RevPAR / rooms_sold / revenue_total
    for a single property and date.
    """
    sql = """
        SELECT
            COALESCE(SUM(total_revenue_etb), 0) AS revenue_total,
            COALESCE(COUNT(*), 0)              AS rooms_sold
        FROM bookings
        WHERE property_code = %s
          AND check_in_date <= %s
          AND check_out_date > %s
          AND booking_status = ANY(%s)
    """
    statuses = list(ACTIVE_STATUSES)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (property_code, target, target, statuses))
            row = cur.fetchone()
            revenue_total = float(row[0]) if row and row[0] is not None else 0.0
            rooms_sold = int(row[1]) if row and row[1] is not None else 0

    adr = revenue_total / rooms_sold if rooms_sold > 0 else 0.0

    # Use total rooms from availability engine for RevPAR:
    from guzo_backend.core.availability_engine import _fetch_rooms_total

    rooms_total = _fetch_rooms_total(property_code)
    revpar = revenue_total / rooms_total if rooms_total > 0 else 0.0

    return DailyKpiOut(
        property_code=property_code,
        date=target,
        adr=adr,
        revpar=revpar,
        rooms_sold=rooms_sold,
        revenue_total=revenue_total,
    )


@router.get("/daily", response_model=DailyKpiOut)
def get_daily_kpi(
    property_code: str,
    date: date,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    kpi = compute_daily_kpi(property_code, date)
    return kpi
