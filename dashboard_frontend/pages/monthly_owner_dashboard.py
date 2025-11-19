# -*- coding: utf-8 -*-
"""
monthly_owner_dashboard.py – Monthly Owner / Investor View (v2.0)
-----------------------------------------------------------------
Streamlit dashboard built on top of:
    guzo_backend.modules.reports_monthly_owner.get_monthly_owner_report

Audience:
    • Hotel owners
    • Asset managers
    • Investors
    • Central system admins (read-only, multi-property)

Core KPIs (per property, per month):
    • Occupancy %
    • ADR (Average Daily Rate)
    • RevPAR
    • Room Revenue (ETB)
    • Room Nights Sold
    • Number of Bookings
    • Payment mix breakdown (if available)
"""

import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from guzo_backend.modules.auth_simple import require_role
from guzo_backend.modules.google_sheets import read_hotels_master
from guzo_backend.modules.reports_monthly_owner import get_monthly_owner_report


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # project root
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(
    page_title="Guzo – Monthly Owner Dashboard",
    layout="wide",
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _current_year_month():
    today = datetime.date.today()
    return today.year, today.month


def _format_month(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


@st.cache_data(ttl=300)
def _load_hotels_visible(allowed_properties: list[str] | None):
    """Return DataFrame of hotels limited by allowed_properties."""
    try:
        df = read_hotels_master()
    except Exception:
        return pd.DataFrame(columns=["Property Code", "Hotel Name"])

    if not allowed_properties or "ALL" in allowed_properties:
        return df

    return df[df["Property Code"].isin(allowed_properties)]


@st.cache_data(ttl=300)
def _load_monthly_report(year: int, month: int, property_code: str):
    return get_monthly_owner_report(year=year, month=month, property_code=property_code)


# ---------------------------------------------------------
# Auth / role
# ---------------------------------------------------------
auth = require_role(["central_admin", "hotel_manager", "portfolio_owner"])
allowed_properties = auth.get("allowed_properties") or []


# ---------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------
def main():
    st.title("📊 Monthly Owner Dashboard")
    st.caption(
        "High-level performance snapshot for hotel owners, investors, and managers – "
        "powered by Guzo Guest Assist & PostgreSQL."
    )

    # ---------------- Sidebar controls ----------------
    st.sidebar.header("Filter")

    cur_year, cur_month = _current_year_month()

    year = st.sidebar.number_input(
        "Year",
        min_value=2023,
        max_value=2100,
        value=cur_year,
        step=1,
    )

    month = st.sidebar.number_input(
        "Month",
        min_value=1,
        max_value=12,
        value=cur_month,
        step=1,
    )

    # Property selection based on allowed_properties + Hotel_Contacts_Master
    df_visible = _load_hotels_visible(allowed_properties)
    if df_visible.empty:
        st.error("No hotels available for this account. Check onboarding / permissions.")
        st.stop()

    property_code = st.sidebar.selectbox(
        "Property",
        options=df_visible["Property Code"].tolist(),
        format_func=lambda code: f"{code} – {df_visible.set_index('Property Code').loc[code, 'Hotel Name']}",
    )

    if st.sidebar.button("🔄 Refresh report"):
        st.experimental_rerun()

    # ---------------- Fetch report ----------------
    st.subheader(f"Summary for {_format_month(year, month)}")

    try:
        report = _load_monthly_report(
            year=year,
            month=month,
            property_code=property_code,
        )
    except Exception as e:
        st.error(f"Could not load monthly report. Error: {e}")
        st.stop()

    # Basic safety check
    if not report:
        st.warning("No data found for this month / property.")
        st.stop()

    hotel_info = report.get("hotel") or report.get("hotel_info") or {}
    hotel_name = hotel_info.get("name") or "Unknown Hotel"

    st.markdown(f"**Hotel:** `{property_code}` – {hotel_name}")

    # ---------------- Top KPI cards ----------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Occupancy %",
            f"{report.get('occupancy_pct', 0):.1f} %",
        )

    with col2:
        st.metric(
            "ADR (ETB)",
            f"{report.get('adr', 0):,.0f}",
        )

    with col3:
        st.metric(
            "RevPAR (ETB)",
            f"{report.get('revpar', 0):,.0f}",
        )

    with col4:
        st.metric(
            "Room Revenue (ETB)",
            f"{report.get('room_revenue_etb', 0):,.0f}",
        )

    # Second row of KPIs
    col5, col6, col7 = st.columns(3)

    with col5:
        st.metric(
            "Room Nights Sold",
            f"{report.get('room_nights_sold', 0):,.0f}",
        )

    with col6:
        st.metric(
            "Bookings",
            f"{report.get('bookings_count', 0):,.0f}",
        )

    with col7:
        st.metric(
            "Rooms Available",
            f"{report.get('rooms_available', 0):,.0f}",
        )

    st.markdown("---")

    # ---------------- Payment mix (if available) ----------------
    st.subheader("💳 Payment Mix")

    by_method = report.get("by_payment_method")

    if not by_method:
        st.info("No payment breakdown data available for this month.")
    else:
        rows = []
        try:
            for label, stats in by_method.items():
                rows.append(
                    {
                        "Method": label,
                        "Bookings": stats.get("bookings", 0),
                        "Room Nights": stats.get("nights", 0),
                        "Revenue (ETB)": stats.get("revenue_etb", 0.0),
                    }
                )
        except Exception:
            rows = []

        if rows:
            df_methods = pd.DataFrame(rows)
            st.dataframe(df_methods, width="stretch")

            try:
                # simple revenue bar chart
                chart_df = df_methods.set_index("Method")[["Revenue (ETB)"]]
                st.bar_chart(chart_df)
            except Exception:
                pass
        else:
            st.info("Payment breakdown structure not recognized. Raw data:")
            st.write(by_method)

    st.markdown("---")

    # ---------------- Example bookings table (if available) ----------------
    st.subheader("📄 Example Bookings")

    example_bookings = report.get("example_bookings") or report.get("bookings_sample")

    if example_bookings:
        df_bookings = pd.DataFrame(example_bookings)
        st.dataframe(df_bookings, width="stretch")
    else:
        st.write("No sample bookings available in this report.")

    # ---------------- Footer ----------------
    st.caption(
        "Guzo Guest Assist – Monthly Owner View · Designed for hotel owners, "
        "investors, and asset managers to see performance at a glance."
    )


if __name__ == "__main__":
    main()
