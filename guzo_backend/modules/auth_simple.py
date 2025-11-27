# guzo_backend/modules/auth_simple.py
"""
Very simple role helper for Guzo dashboards.

Goal:
- Let Streamlit pages ask: "What role is this user?" and
  "Which properties is this user allowed to see?"

Current usage in dashboards:

    from guzo_backend.modules.auth_simple import require_role

    auth = require_role(["central_admin", "portfolio_owner"])
    allowed_properties = auth.get("allowed_properties") or []

For now, in LOCAL DEV mode, we assume:
- You (founder) are "central_admin"
- You can see all demo properties: DRE001, N&N002

Later, you can replace this with real auth based on:
- Google / email login
- API tokens
- Session cookies, etc.
"""

from typing import Any, Dict, Iterable, List
import os


def require_role(allowed_roles: Iterable[str] | None = None) -> Dict[str, Any]:
    """
    Resolve the current user's role + allowed properties.

    Parameters
    ----------
    allowed_roles:
        A list of roles the page is intended for, e.g.
        ["central_admin", "portfolio_owner", "hotel_owner"]

    Returns
    -------
    dict with keys:
        - "role": str
        - "allowed_properties": List[str]

    In local DEV mode:
        - role is taken from env GUZO_DASH_ROLE (default: "central_admin")
        - allowed_properties is a hard-coded list of demo hotels
    """

    # Default role for local dev: you are the central admin / owner.
    role = os.getenv("GUZO_DASH_ROLE", "central_admin")

    # Demo properties – aligned with your current Guzo workflow
    all_demo_properties: List[str] = ["DRE001", "N&N002"]

    # If the current role is not in allowed_roles, you could:
    # - return empty access (what we do now)
    # - or raise an error (future option)
    if allowed_roles and role not in allowed_roles:
        # No access to anything (for now just returns empty list)
        return {
            "role": role,
            "allowed_properties": [],
        }

    # Otherwise, full access to all demo properties
    return {
        "role": role,
        "allowed_properties": all_demo_properties,
    }
