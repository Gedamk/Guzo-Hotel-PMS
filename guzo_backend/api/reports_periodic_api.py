# guzo_backend/api/reports_periodic_api.py

from __future__ import annotations

import datetime as dt
import io
import csv
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from guzo_backend.db.postgres_bookings import get_connection  # you already have this
from guzo_backend.core.auth import verify_admin_token  # small helper you'll add

router = APIRouter(prefix="/reports", tags=["reports-periodic"])

security = HTTPBearer()


def _parse_year_week(year: int, week: int) -> tuple[dt.date, dt.date]:
  """
  Convert ISO year-week to date range [start, end].
  """
  try:
    start = dt.date.fromisocalendar(year, week, 1)  # Monday
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=f"Invalid year/week: {exc}")
  end = start + dt.timedelta(days=6)
  return start, end


def _parse_year_month(year: int, month: int) -> tuple[dt.date, dt.date]:
  """
  Convert year-month to date range [start, end].
  """
  try:
    start = dt.date(year, month, 1)
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=f"Invalid year/month: {exc}")
  # Next month first day - 1 day
  if month == 12:
    next_month = dt.date(year + 1, 1, 1)
  else:
    next_month = dt.date(year, month + 1, 1)
  end = next_month - dt.timedelta(days=1)
  return start, end


def _build_periodic_csv(start: dt.date, end: dt.date) -> bytes:
  """
  Aggregate bookings per hotel & output CSV bytes.
  """
  with get_connection() as conn, conn.cursor() as cur:
    sql = """
      SELECT
        h.id AS hotel_id,
        h.hotel_name,
        b.property_code,
        COUNT(*) AS bookings_count,
        COALESCE(SUM(b.total_revenue_etb::numeric), 0) AS revenue_etb,
        MIN(b.check_in_date) AS first_check_in,
        MAX(b.check_out_date) AS last_check_out
      FROM bookings b
      JOIN hotels h ON h.id = b.hotel_id
      WHERE b.check_in_date <= %s
        AND b.check_out_date >= %s
      GROUP BY h.id, h.hotel_name, b.property_code
      ORDER BY h.hotel_name, b.property_code;
    """
    cur.execute(sql, (end, start))
    rows = cur.fetchall()

  buf = io.StringIO()
  writer = csv.writer(buf)
  writer.writerow(
    [
      "hotel_id",
      "hotel_name",
      "property_code",
      "bookings_count",
      "revenue_etb",
      "first_check_in",
      "last_check_out",
      "period_start",
      "period_end",
    ]
  )
  for r in rows:
    hotel_id, hotel_name, prop_code, count, revenue, first_ci, last_co = r
    writer.writerow(
      [
        hotel_id,
        hotel_name,
        prop_code,
        count,
        str(revenue),
        first_ci.isoformat() if first_ci else "",
        last_co.isoformat() if last_co else "",
        start.isoformat(),
        end.isoformat(),
      ]
    )

  return buf.getvalue().encode("utf-8-sig")


@router.get("/weekly/excel")
def weekly_excel_report(
  year: int,
  week: int,
  creds: HTTPAuthorizationCredentials = Depends(security),
):
  verify_admin_token(creds.credentials)  # simple token check

  start, end = _parse_year_week(year, week)
  content = _build_periodic_csv(start, end)
  filename = f"guzo_weekly_report_{year}-W{week:02d}.csv"

  return Response(
    content=content,
    media_type="application/vnd.ms-excel",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )


@router.get("/monthly/excel")
def monthly_excel_report(
  year: int,
  month: int,
  creds: HTTPAuthorizationCredentials = Depends(security),
):
  verify_admin_token(creds.credentials)

  start, end = _parse_year_month(year, month)
  content = _build_periodic_csv(start, end)
  filename = f"guzo_monthly_report_{year}-{month:02d}.csv"

  return Response(
    content=content,
    media_type="application/vnd.ms-excel",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )
