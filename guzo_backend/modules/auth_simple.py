# -*- coding: utf-8 -*-
"""
auth_simple.py – Simple shared-secret token auth for Guzo API
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class UserContext:
    username: str
    role: str
    property_code: Optional[str] = None


# -------------------------------------------------------
# Token store (DEV MODE ONLY)
# -------------------------------------------------------
API_TOKENS: Dict[str, UserContext] = {
    # CENTRAL ADMIN / PORTFOLIO OWNER
    "admin-secret-123": UserContext(
        username="portfolio_owner",
        role="central_admin",
        property_code=None,
    ),

    # MANAGERS FOR EACH HOTEL
    "dre-manager-secret": UserContext(
        username="dre_manager",
        role="manager",
        property_code="DRE001",
    ),
    "nn-manager-secret": UserContext(
        username="nn_manager",
        role="manager",
        property_code="N&N002",
    ),
}


# -------------------------------------------------------
# Resolve token → UserContext
# -------------------------------------------------------
def resolve_token(token: str) -> Optional[UserContext]:
    return API_TOKENS.get(token)
