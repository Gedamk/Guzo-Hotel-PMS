# -*- coding: utf-8 -*-
"""
guzo_api.auth_deps – Auth / user dependency stubs
-------------------------------------------------
For now this returns a demo user with central_admin role.
Later you can replace with real JWT / DB users.
"""

from typing import List
from pydantic import BaseModel


class User(BaseModel):
    id: str
    role: str
    allowed_properties: List[str]  # e.g. ["DRE001"] or ["ALL"]


def get_current_user() -> User:
    """
    Temporary demo user:
      - role: central_admin
      - allowed_properties: ["ALL"] (can see all hotels)
    Later: read from JWT or session.
    """
    return User(
        id="demo-admin",
        role="central_admin",
        allowed_properties=["ALL"],
    )
