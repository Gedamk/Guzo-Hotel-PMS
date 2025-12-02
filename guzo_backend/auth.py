# guzo_backend/auth.py

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException


# ---------------------------------------------------------------------------
# Simple shared token for admin/dashboard access
# ---------------------------------------------------------------------------

SIMPLE_ADMIN_TOKEN = "admin-secret-123"


def verify_simple_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Very simple token verification used by internal APIs (rooms_api, frontdesk,
    and any other admin/dashboard endpoints).

    Expected header:
        Authorization: Bearer admin-secret-123

    If the token is valid, returns the token string.
    If not, raises HTTPException(401).
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
        )

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format",
        )

    token = authorization[len(prefix) :].strip()
    if token != SIMPLE_ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    return token


# ---------------------------------------------------------------------------
# Optional compatibility helpers for future use
# ---------------------------------------------------------------------------

def verify_admin_or_raise(authorization: Optional[str] = Header(None)) -> None:
    """
    Thin wrapper around verify_simple_token, kept for future compatibility.
    Raises HTTPException if token is missing/invalid.
    """
    _ = verify_simple_token(authorization=authorization)
    # If we get here, token is valid; no return value needed.
