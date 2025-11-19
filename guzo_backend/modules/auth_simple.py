# -*- coding: utf-8 -*-
"""
auth_simple.py – VERY SIMPLE RBAC for Guzo dashboards (demo only!)

This module lets you:
- Log in as one of three roles:
    • Central System Admin       (central_admin)
    • Hotel Manager / GM         (hotel_manager)
    • Portfolio Owner / Investor (portfolio_owner)
- Store auth info in st.session_state["auth"]
- Gate each dashboard page with require_role([...])

For production, replace this with a real auth system
(Auth0, Keycloak, Django/FASTAPI auth, etc.).
"""

import os
import streamlit as st

ROLES = {
    "central_admin": "Central System Admin",
    "hotel_manager": "Hotel Manager / GM",
    "portfolio_owner": "Portfolio Owner / Investor",
}

# Demo PINs – override in .env in real use
CENTRAL_ADMIN_PASS = os.getenv("GUZO_DASH_CENTRAL_PASS", "central-demo")
MANAGER_PASS = os.getenv("GUZO_DASH_MANAGER_PASS", "manager-demo")
OWNER_PASS = os.getenv("GUZO_DASH_OWNER_PASS", "owner-demo")


def _init_auth_state() -> None:
    """Make sure session_state.auth exists."""
    if "auth" not in st.session_state:
        st.session_state["auth"] = {
            "logged_in": False,
            "role": None,
            "allowed_properties": [],  # e.g. ["DRE001", "N&N002"] or ["ALL"]
        }


def login_block() -> None:
    """
    Render a small login UI in the sidebar.
    - If logged in, show role + properties + logout button.
    - If not, show role selection + PIN + property codes.
    """
    _init_auth_state()
    auth = st.session_state["auth"]

    if auth["logged_in"]:
        role_label = ROLES.get(auth["role"], "Unknown")
        props = auth.get("allowed_properties") or []
        props_label = ", ".join(props) if props and props != ["ALL"] else "ALL properties"

        st.sidebar.success(f"Logged in as: {role_label} ({props_label})")

        if st.sidebar.button("🔐 Log out"):
            st.session_state["auth"] = {
                "logged_in": False,
                "role": None,
                "allowed_properties": [],
            }
            st.experimental_rerun()
        return

    # Not logged in – show login form
    st.sidebar.subheader("🔐 Access")

    role_label = st.sidebar.selectbox(
        "I am a:",
        [
            "Central System Admin",
            "Hotel Manager / GM",
            "Portfolio Owner / Investor",
        ],
    )

    password = st.sidebar.text_input("Dashboard PIN / Password", type="password")

    property_codes_raw = st.sidebar.text_input(
        "Property codes (comma separated)",
        value="DRE001",
        help="Example: DRE001 or DRE001,N&N002",
    )

    if st.sidebar.button("Login"):
        code_list = [c.strip() for c in property_codes_raw.split(",") if c.strip()]

        # Map friendly label → internal role
        if role_label == "Central System Admin":
            if password == CENTRAL_ADMIN_PASS:
                auth.update(
                    {
                        "logged_in": True,
                        "role": "central_admin",
                        "allowed_properties": code_list or ["ALL"],
                    }
                )
            else:
                st.sidebar.error("Wrong password for Central System Admin")

        elif role_label == "Hotel Manager / GM":
            if password == MANAGER_PASS:
                auth.update(
                    {
                        "logged_in": True,
                        "role": "hotel_manager",
                        "allowed_properties": code_list,
                    }
                )
            else:
                st.sidebar.error("Wrong password for Hotel Manager / GM")

        elif role_label == "Portfolio Owner / Investor":
            if password == OWNER_PASS:
                auth.update(
                    {
                        "logged_in": True,
                        "role": "portfolio_owner",
                        "allowed_properties": code_list,
                    }
                )
            else:
                st.sidebar.error("Wrong password for Portfolio Owner / Investor")

        st.session_state["auth"] = auth
        st.experimental_rerun()


def require_role(allowed_roles: list[str]):
    """
    Call this at the top of each dashboard page.

    Example:
        from guzo_backend.modules.auth_simple import require_role
        auth = require_role(["central_admin", "hotel_manager"])
        allowed_properties = auth["allowed_properties"]

    If the user is not logged in or not allowed, this function shows
    an error and stops the page.
    """
    _init_auth_state()
    auth = st.session_state.get("auth", {})

    if not auth.get("logged_in"):
        st.error("Please log in via Guzo Control Center to view this page.")
        st.stop()

    if auth.get("role") not in allowed_roles:
        st.error("You do not have permission to view this dashboard.")
        st.stop()

    return auth
