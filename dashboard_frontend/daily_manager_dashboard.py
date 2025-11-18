# -*- coding: utf-8 -*-
"""
daily_manager_dashboard.py – Guzo Daily Manager Dashboard (v1.1)
----------------------------------------------------------------
Streamlit app for hotel managers / owners.

Uses:
 - PostgreSQL (hotels + bookings tables)
 - reports_daily_manager.get_daily_manager_report()

Shows:
 - Key KPIs (Occupancy, ADR, RevPAR, Room Revenue)
 - Arrivals / Departures / In-House lists
"""

import os
import datetime
import logging

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from guzo_backend.modules.postgres_bookings import get_connection
from guzo_backend.modules.reports_daily_manager import get_daily_manager_report

# -------------------------------------------------
# ENV + LOGGING
# -------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "../.env")
# Fallback if running from project root
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), "../..", ".env")

load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# -------------------------------------------------
# HELPER: Load hotels list from Postgres
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def load_hotels_from_db():
    """
    Return a list of dicts: {"property_code": "...", "name": "..."}.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT property_code, name
                    FROM hotels
                    ORDER BY property_code;
                    """
                )
                rows = cur.fetchall()
        hotels = [
            {"property_code": r[0], "name": r[1]}
            for r in rows
        ]
        return hotels
    finally:
        conn.close()


# -------------------------------------------------
# MAIN STREAMLIT APP
# -------------------------------------------------
def main():
    st.set_page_config(
        page_title="Guzo – Daily Manager Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛎️ Guzo Daily Manager Dashboard")
    st.caption(
        "Daily PMS-style summary: occupancy, arrivals, departures, in-house guests, "
        "and room revenue – designed for manager / owner / finance / tax reporting."
    )

    # ------------------------------
    # Sidebar controls
    # ------------------------------
    st.sidebar.header("Filters")

    hotels = load_hotels_from_db()
    if not hotels:
        st.sidebar.error("No hotels found in Postgres 'hotels' table.")
        st.stop()

    hotel_labels = [
        f"{h['property_code']} – {h['name']}" for h in hotels
    ]
    selected_label = st.sidebar.selectbox(
        "Select hotel",
        hotel_labels,
        index=0,
    )

    selected_hotel = hotels[hotel_labels.index(selected_label)]
    property_code = selected_hotel["property_code"]

    today = datetime.date.today()
    report_date = st.sidebar.date_input(
        "Report date",
        value=today,
        max_value=today + datetime.timedelta(days=365),  # allow future bookings
    )

    if st.sidebar.button("📊 Generate report"):
        run_report(property_code, report_date)
    else:
        # Auto run on initial load
        run_report(property_code, report_date)


# -------------------------------------------------
# RENDER REPORT
# -------------------------------------------------
def run_report(property_code: str, report_date: datetime.date):
    st.subheader(
        f"📅 Daily Report – {report_date.isoformat()} | Property: {property_code}"
    )

    with st.spinner("Loading daily statistics from Postgres..."):
        report = get_daily_manager_report(
            report_date.isoformat(),
            property_code=property_code,
        )

    if not report:
        st.warning("No bookings found for this date / property.")
        return

    summary = report.get("summary", {})
    arrivals = report.get("arrivals", [])
    departures = report.get("departures", [])
    in_house = report.get("in_house", [])

    # ------------------------------
    # KPI Row
    # ------------------------------
    st.markdown("### 🔢 Key Performance Indicators")

    kpi_cols = st.columns(6)

    kpi_cols[0].metric(
        "Occupancy %",
        f"{summary.get('occupancy_pct', 0):.1f}%",
    )
    kpi_cols[1].metric(
        "ADR (ETB)",
        f"{summary.get('adr', 0):,.0f}",
    )
    kpi_cols[2].metric(
        "RevPAR (ETB)",
        f"{summary.get('revpar', 0):,.0f}",
    )
    kpi_cols[3].metric(
        "Room Revenue (ETB)",
        f"{summary.get('room_revenue_etb', 0):,.0f}",
    )
    kpi_cols[4].metric(
        "Arrivals",
        summary.get("arrivals", 0),
    )
    kpi_cols[5].metric(
        "Departures",
        summary.get("departures", 0),
    )

    st.markdown("---")

    # ------------------------------
    # Arrivals / Departures / In-House
    # ------------------------------
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### ✈️ Arrivals")
        if arrivals:
            df_arrivals = pd.DataFrame(arrivals)
            st.dataframe(df_arrivals, width="stretch")
        else:
            st.info("No arrivals for this date.")

        st.markdown("### 🧳 In-House Guests")
        if in_house:
            df_in_house = pd.DataFrame(in_house)
            st.dataframe(df_in_house, width="stretch")
        else:
            st.info("No in-house guests for this date.")

    with col_b:
        st.markdown("### 🚪 Departures")
        if departures:
            df_departures = pd.DataFrame(departures)
            st.dataframe(df_departures, width="stretch")
        else:
            st.info("No departures for this date.")

    st.markdown("---")

    # ------------------------------
    # Raw summary JSON (debug / export)
    # ------------------------------
    with st.expander("🔍 Technical summary (JSON) – for debugging / integrations"):
        st.json(report)


if __name__ == "__main__":
    main()
