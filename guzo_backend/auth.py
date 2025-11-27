# guzo_backend/auth.py
#
# Simple admin auth dependency for internal dashboard + front desk APIs.
# Uses a static bearer token (default: "admin-secret-123") or GUZO_ADMIN_TOKEN env var.

import os
from fastapi import Header, HTTPException, status


ADMIN_TOKEN = os.getenv("GUZO_ADMIN_TOKEN", "admin-secret-123")


async def get_current_admin(authorization: str = Header(None)):
    """
    Very simple admin check:
      - Expect header:  Authorization: Bearer admin-secret-123
      - If missing or wrong => 401 / 403

    Used by:
      - /reports/portfolio
      - /frontdesk/* endpoints
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    token = authorization.split(" ", 1)[1].strip()

    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    # We don't need a full user object yet; just return a simple marker.
    return {"role": "admin"}
