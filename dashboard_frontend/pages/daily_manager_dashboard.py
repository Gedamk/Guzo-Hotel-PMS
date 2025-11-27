# -*- coding: utf-8 -*-
"""
daily_manager_dashboard.py – Daily Manager View (v2.1)

Powered by:
    guzo_backend.modules.reports_daily_manager.get_daily_manager_report()

Data source:
    • PostgreSQL (via backend report module)
    • NO direct Google Sheets dependency anymore

Audience:
    • Hotel Managers / GMs
    • Central System Admin (read-only)
"""

import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Auth – try real helper, fall back to a local stub in dev
# -------------------------------------------------------------------
try:
    from guzo_backend.modules.auth_simple import require_role  # type: ignore
except ImportError:
    # DEV / LOCAL STUB so dashboard works even if auth_simple
    # doesn't yet define require_role().
    def require_role(roles: list[str]):
        """
        Local fallback for development:
        - Pretend the user is a manager with access to both hotels.
        """
        return {
            "user": "dev_local",
            "role": "hotel_manager",
            "allowed_properties": ["DRE001", "N&N002"],
        }

from guzo_backend.modules.reports_daily_manager import get_daily_manager_report

# Optional: future Postgres-based hotel helper
try:
    from guzo_backend.modules.postgres_hotels import get_hotels_df  # type: ignore
except ImportError:
    get_hotels_df = None  # type: ignore

# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # project root
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(
    page_title="Guzo – Daily Manager Dashboard",
    layout="wide",
)

# -------------------------------------------------------------------
# Role & allowed properties
# -------------------------------------------------------------------
auth = require_role(["central_admin", "hotel_manager"])
allowed_properties = auth.get("allowed_properties") or []

# -------------------------------------------------------------------
# Hotel list (Postgres-first, then safe fallback)
# -------------------------------------------------------------------
def _fallback_hotels_df() -> pd.DataFrame:
    """
    Fallback list when we don't yet have a Postgres hotel master helper.

    Extend this list as you onboard more properties.
    """
    hotels = [
        {"property_code": "DRE001", "hotel_name": "Dream Big Hotel"},
        {"property_code": "N&N002", "hotel_name": "N&N Luxury Hotel"},
    ]
    return pd.DataFrame(hotels)


if get_hotels_df:
    # Preferred future path – read from PostgreSQL
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
    # Current stage – clean static list, no Google Sheets dependency
    df_hotels = _fallback_hotels_df().rename(
        columns={
            "property_code": "Property Code",
            "hotel_name": "Hotel Name",
        }
    )

# Apply role-based restriction
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
# Sidebar filters
# -------------------------------------------------------------------
st.sidebar.header("📅 Daily Manager Filters")

property_code = st.sidebar.selectbox(
    "Property",
    options=df_visible["Property Code"].tolist(),
    format_func=lambda code: (
        f"{code} – "
        f"{df_visible.set_index('Property Code').loc[code, 'Hotel Name']}"
    ),
)

report_date = st.sidebar.date_input(
    "Business Date",
    value=datetime.date.today(),
)

if st.sidebar.button("🔄 Refresh"):
    st.experimental_rerun()

# -------------------------------------------------------------------
# Load report (PostgreSQL via backend report module)
# -------------------------------------------------------------------
try:
    report = get_daily_manager_report(
        date=report_date,
        property_code=property_code,
    )
except Exception as e:
    st.error(f"Could not load daily report from backend. Error: {e}")
    st.stop()

hotel_info = report.get("hotel") or {}
hotel_name = hotel_info.get("name", "Unknown Hotel")

st.title("📅 Daily Manager Dashboard")
st.caption(
    f"Hotel: `{property_code}` – {hotel_name} · "
    f"Business date: {report_date.isoformat()}"
)

# -------------------------------------------------------------------
# Top KPIs (FO + Revenue)
# -------------------------------------------------------------------
summary = report.get("summary") or report  # backward compatibility

rooms_total = summary.get("rooms_total", 0)
rooms_in_house = summary.get("rooms_in_house", 0)
occupancy_pct = summary.get("occupancy_pct", 0.0)
room_revenue = summary.get("room_revenue_etb", 0.0)
adr = summary.get("adr", 0.0)
revpar = summary.get("revpar", 0.0)
arrivals = summary.get("arrivals", 0)
departures = summary.get("departures", 0)
in_house = summary.get("in_house", 0)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Rooms in House", f"{rooms_in_house}/{rooms_total}")
with c2:
    st.metric("Occupancy %", f"{occupancy_pct:.1f} %")
with c3:
    st.metric("ADR (ETB)", f"{adr:,.0f}")
with c4:
    st.metric("RevPAR (ETB)", f"{revpar:,.0f}")

c5, c6, c7 = st.columns(3)
with c5:
    st.metric("Arrivals", f"{arrivals}")
with c6:
    st.metric("Departures", f"{departures}")
with c7:
    st.metric("In-House Guests", f"{in_house}")

st.markdown("---")

# -------------------------------------------------------------------
# Arrivals / Departures / In-House tables
# -------------------------------------------------------------------
def _show_booking_table(label: str, rows: list[dict]):
    st.subheader(label)
    if not rows:
        st.info(f"No {label.lower()} for this date.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, height=260, use_container_width=True)


_arrivals = report.get("arrivals_detail") or report.get("arrivals_list") or []
_departures = report.get("departures_detail") or report.get("departures_list") or []
_in_house = report.get("in_house_detail") or report.get("in_house_list") or []

tab1, tab2, tab3 = st.tabs(["Arrivals", "Departures", "In-House"])

with tab1:
    _show_booking_table("Arrivals", _arrivals)

with tab2:
    _show_booking_table("Departures", _departures)

with tab3:
    _show_booking_table("In-House", _in_house)

st.markdown("---")

# -------------------------------------------------------------------
# Simple revenue vs rooms visualization (same-day)
# -------------------------------------------------------------------
st.subheader("📈 Today’s Revenue Snapshot")

chart_df = pd.DataFrame(
    {
        "Metric": ["Room Revenue (ETB)", "Rooms in House"],
        "Value": [room_revenue, rooms_in_house],
    }
)
fig = px.bar(
    chart_df,
    x="Metric",
    y="Value",
    title="Revenue vs. Rooms in House",
    text_auto=True,
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(
    "Guzo Guest Assist – Daily Front-Office View · Helps duty managers see "
    "today’s business at a glance (arrivals, departures, ADR, RevPAR) using "
    "PostgreSQL as the source of truth."
)
