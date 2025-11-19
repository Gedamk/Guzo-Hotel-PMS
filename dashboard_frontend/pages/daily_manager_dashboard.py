# -*- coding: utf-8 -*-
"""
daily_manager_dashboard.py – Daily Manager View (v2.0)

Powered by:
    guzo_backend.modules.reports_daily_manager.get_daily_manager_report()

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

from guzo_backend.modules.auth_simple import require_role
from guzo_backend.modules.reports_daily_manager import get_daily_manager_report
from guzo_backend.modules.google_sheets import read_hotels_master

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
# Auth / role
# -------------------------------------------------------------------
auth = require_role(["central_admin", "hotel_manager"])
allowed_properties = auth.get("allowed_properties") or []

# -------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------
st.sidebar.header("📅 Daily Manager Filters")

# Hotels list from master sheet
try:
    df_hotels = read_hotels_master()
except Exception:
    df_hotels = pd.DataFrame(columns=["Property Code", "Hotel Name"])

if "ALL" in allowed_properties or not allowed_properties:
    df_visible = df_hotels
else:
    df_visible = df_hotels[df_hotels["Property Code"].isin(allowed_properties)]

if df_visible.empty:
    st.error("No hotels available for your account. Check allowed properties or onboarding.")
    st.stop()

property_code = st.sidebar.selectbox(
    "Property",
    options=df_visible["Property Code"].tolist(),
    format_func=lambda code: f"{code} – {df_visible.set_index('Property Code').loc[code, 'Hotel Name']}",
)

report_date = st.sidebar.date_input(
    "Business Date",
    value=datetime.date.today(),
)

if st.sidebar.button("🔄 Refresh"):
    st.experimental_rerun()

# -------------------------------------------------------------------
# Load report
# -------------------------------------------------------------------
try:
    report = get_daily_manager_report(date=report_date, property_code=property_code)
except Exception as e:
    st.error(f"Could not load daily report. Error: {e}")
    st.stop()

hotel_info = report.get("hotel") or {}
hotel_name = hotel_info.get("name", "Unknown Hotel")

st.title("📅 Daily Manager Dashboard")
st.caption(
    f"Hotel: `{property_code}` – {hotel_name} · "
    f"Business date: {report_date.isoformat()}"
)

# -------------------------------------------------------------------
# Top KPIs
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
    st.dataframe(df, height=260, width="stretch")


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

# Construct a tiny 2-bar chart to show Revenue vs Rooms in House
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
st.plotly_chart(fig)

st.markdown("---")
st.caption(
    "Guzo Guest Assist – Daily Front-Office View · Help duty managers see "
    "today’s business at a glance (arrivals, departures, ADR, RevPAR)."
)
