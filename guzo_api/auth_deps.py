# -*- coding: utf-8 -*-
"""
auth_deps.py – Authentication & Role-Based Access Control for Guzo API
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from guzo_backend.modules.auth_simple import UserContext, resolve_token


security = HTTPBearer(auto_error=False)


# -------------------------------------------------------
# Helper: extract raw Bearer token
# -------------------------------------------------------
def _extract_token(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization scheme must be Bearer",
        )

    return credentials.credentials


# -------------------------------------------------------
# Return UserContext for any valid token
# -------------------------------------------------------
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserContext:
    raw_token = _extract_token(credentials)
    user_context = resolve_token(raw_token)

    if user_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

    return user_context


# -------------------------------------------------------
# Require CENTRAL ADMIN (Portfolio owner)
# -------------------------------------------------------
def require_central_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    if user.role != "central_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Central admin privileges required",
        )
    return user


# -------------------------------------------------------
# Require hotel-level access (manager or central admin)
# -------------------------------------------------------
def require_hotel_access(
    property_code: str,
    user: UserContext = Depends(get_current_user),
) -> UserContext:

    # Central admin → always allowed
    if user.role == "central_admin":
        return user

    # Manager must match hotel code
    if user.role == "manager":
        if user.property_code is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager not linked to any hotel",
            )

        if user.property_code != property_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to view this hotel's report",
            )

        return user

    # Other roles blocked
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )
