# -*- coding: utf-8 -*-
"""
guzo_control_center.py – Main entry for all Guzo dashboards (v2.0)

This is the "home page" for:
- Central System Admin
- Hotel Managers / GMs
- Portfolio Owners / Investors

From here, users log in and navigate to:
- Central Operations dashboard
- Daily Manager dashboard
- Monthly Owner dashboard
- Portfolio Owner dashboard
"""

import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from guzo_backend.modules import google_sheets
from guzo_backend.modules.auth_simple import login_block

# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # project root
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(
    page_title="Guzo Control Center",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# Auth block in sidebar
# -------------------------------------------------------------------
login_block()
auth = st.session_state.get("auth", {})
role = auth.get("role")
allowed_properties = auth.get("allowed_properties", [])

# -------------------------------------------------------------------
# Sidebar navigation
# -------------------------------------------------------------------
st.sidebar.markdown("### 🧭 Navigation")

if not auth.get("logged_in"):
    st.sidebar.info("Log in above to open dashboards.")
else:
    # Central Operations always first for internal users
    if role in ("central_admin", "hotel_manager"):
        st.sidebar.page_link(
            "pages/central_dashboard.py",
            label="🏨 Central Operations Dashboard",
        )
        st.sidebar.page_link(
            "pages/daily_manager_dashboard.py",
            label="📅 Daily Manager Dashboard",
        )

    if role in ("central_admin", "hotel_manager", "portfolio_owner"):
        st.sidebar.page_link(
            "pages/monthly_owner_dashboard.py",
            label="📊 Monthly Owner Dashboard",
        )

    if role in ("central_admin", "portfolio_owner"):
        st.sidebar.page_link(
            "pages/portfolio_owner_dashboard.py",
            label="🌍 Portfolio Owner Dashboard",
        )

st.sidebar.markdown("---")
st.sidebar.caption("Tip: Treat this Control Center as the main entry for managers and owners.")

# -------------------------------------------------------------------
# Main content – hero + quick overview
# -------------------------------------------------------------------
st.title("🛎️ Guzo Control Center")
st.caption(
    "Central access for hotel managers, owners, and portfolio investors – "
    "daily operations, monthly KPIs, and multi-property analytics."
)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📌 Quick Overview")

    st.markdown("### 🏨 Central Operations")
    st.markdown(
        """
- Real-time bot & guest activity  
- Notifications log (alerts, issues)  
- Sheet & system health indicators  
- Duty manager & front-office status  
        """
    )

    if role in ("central_admin", "hotel_manager"):
        st.link_button(
            "➡️ Open Central Operations Dashboard",
            url="?page=central_dashboard",
        )
    else:
        st.info("Central Operations is visible to Central Admins and Hotel Managers.")

with col_right:
    st.subheader("📈 Performance & Ownership")

    st.markdown(
        """
- **Daily Manager**: arrivals, departures, in-house, ADR, RevPAR  
- **Monthly Owner**: occupancy %, ADR, RevPAR, revenue per hotel  
- **Portfolio**: cross-hotel revenue, mix, and trends  
- Ideal for GMs, owners & finance teams  
        """
    )

    if role in ("central_admin", "hotel_manager"):
        st.link_button(
            "📅 Open Daily Manager Dashboard →",
            url="?page=daily_manager_dashboard",
        )

    if role in ("central_admin", "hotel_manager", "portfolio_owner"):
        st.link_button(
            "📊 Open Monthly Owner Dashboard →",
            url="?page=monthly_owner_dashboard",
        )

    if role in ("central_admin", "portfolio_owner"):
        st.link_button(
            "🌍 Open Portfolio Owner Dashboard →",
            url="?page=portfolio_owner_dashboard",
        )

st.markdown("---")

# -------------------------------------------------------------------
# Small stats from Hotel_Contacts_Master (optional)
# -------------------------------------------------------------------
st.subheader("🏘️ Portfolio Snapshot")

total_hotels = None
try:
    df_hotels = google_sheets.read_hotels_master()
    total_hotels = len(df_hotels.index)
except Exception:
    df_hotels = None

today = datetime.date.today().isoformat()
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Today", today)

with col_b:
    st.metric("Total Hotels Onboarded", total_hotels or 0)

with col_c:
    props_label = (
        "ALL"
        if (allowed_properties == ["ALL"] or not allowed_properties)
        else ", ".join(allowed_properties)
    )
    st.metric("Properties in View", props_label)

st.caption(
    "Later we can extend this snapshot with live room nights, today’s arrivals, "
    "and any system alerts across the portfolio."
)
