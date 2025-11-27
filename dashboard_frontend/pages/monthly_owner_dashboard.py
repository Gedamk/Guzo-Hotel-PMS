# -*- coding: utf-8 -*-
"""
monthly_owner_dashboard.py – Monthly Owner / GM View (v2.0)

Goal:
    • High-level monthly performance per hotel
    • Same core KPIs as portfolio React dashboard:
        - bookings_count
        - room_nights_sold
        - room_revenue_etb
        - adr
        - revpar
        - occupancy_pct

Data source:
    • PostgreSQL via:
        guzo_backend.modules.reports_monthly_owner.get_monthly_owner_report()
"""

import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Auth – real helper if available, else local stub
# -------------------------------------------------------------------
try:
    from guzo_backend.modules.auth_simple import require_role  # type: ignore
except ImportError:
    def require_role(roles: list[str]):
        """
        Local fallback:
        - Treat user as owner/central admin with both properties.
        """
        return {
            "user": "dev_owner",
            "role": "portfolio_owner",
            "allowed_properties": ["DRE001", "N&N002"],
        }

from guzo_backend.modules.reports_monthly_owner import (
    get_monthly_owner_report,
)

# Optional: future Postgres-based hotel helper
try:
    from guzo_backend.modules.postgres_hotels import get_hotels_df  # type: ignore
except ImportError:
    get_hotels_df = None  # type: ignore

# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(
    page_title="Guzo – Monthly Owner Dashboard",
    layout="wide",
)

# -------------------------------------------------------------------
# Role and allowed properties
# -------------------------------------------------------------------
auth = require_role(["central_admin", "portfolio_owner", "hotel_owner"])
allowed_properties = auth.get("allowed_properties") or []

# -------------------------------------------------------------------
# Hotel list (Postgres-first, then safe fallback)
# -------------------------------------------------------------------
def _fallback_hotels_df() -> pd.DataFrame:
    hotels = [
        {"property_code": "DRE001", "hotel_name": "Dream Big Hotel"},
        {"property_code": "N&N002", "hotel_name": "N&N Luxury Hotel"},
    ]
    return pd.DataFrame(hotels)


if get_hotels_df:
    try:
        df_hotels = get_hotels_df()
        df_hotels = df_hotels.rename(
            columns={
                "property_code": "Property Code",
                "hotel_name": "Hotel Name",
            }
        )
    except Exception:
        df_hotels = _fallback_hotels_df().rename(
            columns={
                "property_code": "Property Code",
                "hotel_name": "Hotel Name",
            }
        )
else:
    df_hotels = _fallback_hotels_df().rename(
        columns={
            "property_code": "Property Code",
            "hotel_name": "Hotel Name",
        }
    )

if "ALL" in allowed_properties or not allowed_properties:
    df_visible = df_hotels
else:
    df_visible = df_hotels[df_hotels["Property Code"].isin(allowed_properties)]

if df_visible.empty:
    st.error(
        "No hotels available for your account. "
        "Check allowed properties or onboarding."
    )
    st.stop()

# -------------------------------------------------------------------
# Sidebar filters: hotel + year + month
# -------------------------------------------------------------------
st.sidebar.header("📆 Monthly Owner Filters")

property_code = st.sidebar.selectbox(
    "Property",
    options=df_visible["Property Code"].tolist(),
    format_func=lambda code: (
        f"{code} – "
        f"{df_visible.set_index('Property Code').loc[code, 'Hotel Name']}"
    ),
)

today = datetime.date.today()
year = st.sidebar.number_input(
    "Year",
    min_value=2023,
    max_value=today.year + 1,
    value=today.year,
    step=1,
)

month = st.sidebar.number_input(
    "Month",
    min_value=1,
    max_value=12,
    value=today.month,
    step=1,
)

if st.sidebar.button("🔄 Refresh"):
    st.experimental_rerun()

month_label = f"{year}-{str(month).zfill(2)}"

# -------------------------------------------------------------------
# Load monthly report
# -------------------------------------------------------------------
try:
    report = get_monthly_owner_report(
        year=year,
        month=month,
        property_code=property_code,
    )
except Exception as e:
    st.error(f"Could not load monthly owner report. Error: {e}")
    st.stop()

hotel_info = report.get("hotel") or {}
hotel_name = hotel_info.get("name", "Unknown Hotel")

st.title("📆 Monthly Owner / GM Dashboard")
st.caption(
    f"Hotel: `{property_code}` – {hotel_name} · "
    f"Month: {month_label}"
)

# -------------------------------------------------------------------
# KPIs
# -------------------------------------------------------------------
summary = report.get("summary") or report

bookings = summary.get("bookings_count", 0)
room_nights = summary.get("room_nights_sold", 0.0)
room_revenue = summary.get("room_revenue_etb", 0.0)
adr = summary.get("adr", 0.0)
revpar = summary.get("revpar", 0.0)
occupancy_pct = summary.get("occupancy_pct", 0.0)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Bookings", f"{bookings}")
with c2:
    st.metric("Room Nights Sold", f"{room_nights:,.0f}")
with c3:
    st.metric("Room Revenue (ETB)", f"{room_revenue:,.0f}")

c4, c5, c6 = st.columns(3)
with c4:
    st.metric("ADR (ETB)", f"{adr:,.0f}")
with c5:
    st.metric("RevPAR (ETB)", f"{revpar:,.0f}")
with c6:
    st.metric("Occupancy %", f"{occupancy_pct*100:.1f} %")

st.markdown("---")

# -------------------------------------------------------------------
# Optional daily trend (if backend provides it)
# -------------------------------------------------------------------
daily_trend = report.get("daily_trend") or []

if daily_trend:
    st.subheader("📈 Daily Room Revenue (ETB)")
    df_trend = pd.DataFrame(daily_trend)
    fig = px.line(
        df_trend,
        x="date",
        y="room_revenue_etb",
        markers=True,
        title=f"Daily Revenue – {month_label}",
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.caption(
    "Guzo Guest Assist – Monthly Owner View · Aligned with global PMS metrics "
    "(Bookings, Room Nights, Revenue, ADR, RevPAR, Occupancy) using PostgreSQL "
    "as the main source of truth."
)
