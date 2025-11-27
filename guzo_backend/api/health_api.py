# guzo_backend/api/health_api.py

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from guzo_backend.db.postgres_bookings import get_connection

router = APIRouter(prefix="/system", tags=["health"])


@router.get("/health")
def health_check():
  """
  Simple health check:
    - DB connectivity
    - Current time
  """
  db_ok = False
  db_error = None

  try:
    with get_connection() as conn, conn.cursor() as cur:
      cur.execute("SELECT 1;")
      cur.fetchone()
    db_ok = True
  except Exception as exc:  # noqa: BLE001
    db_ok = False
    db_error = str(exc)

  return {
    "status": "ok" if db_ok else "degraded",
    "time_utc": dt.datetime.utcnow().isoformat(),
    "checks": {
      "database": {
        "ok": db_ok,
        "error": db_error,
      }
    },
  }
