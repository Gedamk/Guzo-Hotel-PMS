# -*- coding: utf-8 -*-
"""
portfolio_owner_dashboard.py – Multi-Property Owner / Group Dashboard (v2.0)
-----------------------------------------------------------------------------

Streamlit dashboard for portfolio-level analytics across all hotels.

Data source:
    guzo_backend.modules.reports_portfolio_owner.get_portfolio_owner_report()

Features:
    - Period selector (year + optional month)
    - Top-level KPIs (Revenue, ADR, RevPAR, Occupancy, Nights, Bookings)
    - Per-hotel KPI table with sorting
    - Revenue by hotel
    - Revenue by payment method
    - Daily revenue & room nights trend

Audience:
    - Hotel group owners
    - Multi-property Airbnb / lodge hosts
    - Regional managers
    - Central system admins (read-only, portfolio scope)
"""

import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from guzo_backend.modules.auth_simple import require_role
from guzo_backend.modules.reports_portfolio_owner import get_portfolio_owner_report


# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # project root
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(
    page_title="Guzo – Portfolio Owner Dashboard",
    layout="wide",
)


# -------------------------------------------------------------------
# Caching layer
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_portfolio_report_cached(year: int, month: int | None, property_filter: list[str] | None):
    """
    Cache wrapper around get_portfolio_owner_report.
    If property_filter is provided, the backend can later be extended to limit to those codes.
    For now, we call the full report and filter in the UI layer where needed.
    """
    report = get_portfolio_owner_report(year=year, month=month)
    if not property_filter or property_filter == ["ALL"]:
        return report

    # Filter per_hotel + daily_trend + sample_bookings by property_code if available
    per_hotel = report.get("per_hotel") or []
    per_hotel = [h for h in per_hotel if h.get("property_code") in property_filter]

    daily_trend = report.get("daily_trend") or []
    # If your daily_trend has property_code, you could also filter; for now assume portfolio-level.

    sample = report.get("sample_bookings") or []
    sample = [b for b in sample if b.get("property_code") in property_filter]

    report = dict(report)  # shallow copy
    report["per_hotel"] = per_hotel
    report["daily_trend"] = daily_trend
    report["sample_bookings"] = sample
    return report


# -------------------------------------------------------------------
# Role / auth
# -------------------------------------------------------------------
auth = require_role(["central_admin", "portfolio_owner"])
allowed_properties = auth.get("allowed_properties") or []


# -------------------------------------------------------------------
# Layout helpers
# -------------------------------------------------------------------
def _kpi_card(label: str, value, suffix: str = "", help_text: str | None = None):
    """Simple KPI card using metric."""
    st.metric(
        label=label,
        value=f"{value}{suffix}" if isinstance(value, (int, float)) else value,
        help=help_text,
    )


# -------------------------------------------------------------------
# Main App
# -------------------------------------------------------------------
def main():
    st.title("🏨 Guzo Portfolio Owner Dashboard")
    st.caption(
        "Unified performance view across all hotels – revenue, occupancy, ADR, RevPAR, and payment mix."
    )

    # Sidebar filters
    today = datetime.date.today()
    st.sidebar.header("📅 Period")

    year = st.sidebar.selectbox(
        "Year",
        options=list(range(today.year - 3, today.year + 1)),
        index=3,  # current year
    )

    month_option = st.sidebar.selectbox(
        "Month (optional)",
        options=["Full Year"] + [f"{m:02d} – {datetime.date(2000, m, 1).strftime('%B')}" for m in range(1, 13)],
        index=today.month,
    )

    if month_option == "Full Year":
        month = None
    else:
        month = int(month_option.split(" – ")[0])

    # Property scope info
    props_label = (
        "ALL properties"
        if (not allowed_properties or allowed_properties == ["ALL"])
        else ", ".join(allowed_properties)
    )
    st.sidebar.info(f"Property scope for this account: {props_label}")

    st.sidebar.caption(
        "Tip: As a portfolio owner you typically see all your hotels; "
        "central admin may see every property in the system."
    )

    # Load report
    report = load_portfolio_report_cached(year, month, allowed_properties or ["ALL"])

    summary = report["summary"]
    per_hotel = report["per_hotel"]
    by_payment = report["by_payment_method"]
    daily_trend = report["daily_trend"]

    period = report["period"]
    period_label = f"{period['start_date']} → {period['end_date']}"

    st.subheader(f"📊 Portfolio Summary – {period_label}")

    # Top KPIs
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        _kpi_card(
            "Total Room Revenue (ETB)",
            f"{summary['room_revenue_etb']:,.0f}",
        )
    with c2:
        _kpi_card(
            "Room Nights Sold",
            f"{summary['room_nights_sold']:,.0f}",
        )
    with c3:
        _kpi_card(
            "Bookings",
            f"{summary['bookings_count']:,.0f}",
        )
    with c4:
        _kpi_card(
            "Portfolio ADR (ETB)",
            f"{summary['adr']:,.0f}",
            help_text="Average Daily Rate across all properties",
        )
    with c5:
        _kpi_card(
            "Portfolio RevPAR (ETB)",
            f"{summary['revpar']:,.0f}",
            help_text="Revenue Per Available Room",
        )
    with c6:
        _kpi_card(
            "Occupancy (%)",
            f"{summary['occupancy_pct']:.2f}",
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Per-hotel table and ranking
    # ------------------------------------------------------------------
    st.subheader("🏨 Per-Hotel Performance")

    if per_hotel:
        df_hotels = pd.DataFrame(per_hotel)
        df_hotels_display = df_hotels[
            [
                "property_code",
                "hotel_name",
                "bookings_count",
                "room_nights_sold",
                "room_revenue_etb",
                "adr",
                "revpar",
                "occupancy_pct",
            ]
        ].copy()

        df_hotels_display.rename(
            columns={
                "property_code": "Property Code",
                "hotel_name": "Hotel Name",
                "bookings_count": "Bookings",
                "room_nights_sold": "Room Nights",
                "room_revenue_etb": "Revenue (ETB)",
                "adr": "ADR (ETB)",
                "revpar": "RevPAR (ETB)",
                "occupancy_pct": "Occupancy (%)",
            },
            inplace=True,
        )

        df_hotels_display["Revenue (ETB)"] = df_hotels_display["Revenue (ETB)"].round(0)
        df_hotels_display["ADR (ETB)"] = df_hotels_display["ADR (ETB)"].round(0)
        df_hotels_display["RevPAR (ETB)"] = df_hotels_display["RevPAR (ETB)"].round(0)
        df_hotels_display["Occupancy (%)"] = df_hotels_display["Occupancy (%)"].round(2)

        st.dataframe(
            df_hotels_display.sort_values("Revenue (ETB)", ascending=False),
            height=350,
            width="stretch",
        )

        # Quick ranking text
        best_revenue = df_hotels_display.sort_values(
            "Revenue (ETB)", ascending=False
        ).iloc[0]
        st.success(
            f"🏆 **Top Revenue Hotel:** {best_revenue['Hotel Name']} "
            f"({best_revenue['Property Code']}) – ETB {best_revenue['Revenue (ETB)']:,.0f}"
        )
    else:
        st.info("No hotel data available for the selected period and property scope.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    c_left, c_right = st.columns(2)

    # Revenue by Hotel
    with c_left:
        st.subheader("💰 Revenue by Hotel")
        if per_hotel:
            df_rev = pd.DataFrame(per_hotel)
            fig = px.bar(
                df_rev,
                x="hotel_name",
                y="room_revenue_etb",
                color="hotel_name",
                labels={"hotel_name": "Hotel", "room_revenue_etb": "Revenue (ETB)"},
                title="Room Revenue by Property",
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig)
        else:
            st.info("No revenue data to display.")

    # Revenue by Payment Method
    with c_right:
        st.subheader("💳 Revenue by Payment Method")
        if by_payment:
            df_pay = pd.DataFrame(by_payment)
            fig2 = px.pie(
                df_pay,
                names="payment_method",
                values="revenue_etb",
                title="Revenue Mix by Payment Method",
            )
            st.plotly_chart(fig2)
        else:
            st.info("No payment breakdown available.")

    st.markdown("---")

    # Daily Trend
    st.subheader("📈 Daily Trend – Revenue & Room Nights")
    if daily_trend:
        df_trend = pd.DataFrame(daily_trend)
        df_trend["date"] = pd.to_datetime(df_trend["date"])

        fig3 = px.line(
            df_trend,
            x="date",
            y="room_revenue_etb",
            labels={"date": "Date", "room_revenue_etb": "Revenue (ETB)"},
            title="Daily Room Revenue",
        )
        st.plotly_chart(fig3)

        fig4 = px.line(
            df_trend,
            x="date",
            y="room_nights",
            labels={"date": "Date", "room_nights": "Room Nights"},
            title="Daily Room Nights Sold",
        )
        st.plotly_chart(fig4)
    else:
        st.info("No daily trend data available for the selected period.")

    st.markdown("---")

    # Debug sample (optional, collapsible)
    with st.expander("🔍 Debug: Sample Bookings (first 10)"):
        df_sample = pd.DataFrame(report.get("sample_bookings") or [])
        if not df_sample.empty:
            st.dataframe(df_sample, width="stretch")
        else:
            st.write("No sample bookings available.")

    st.caption(
        "Guzo Guest Assist – Portfolio Owner View · Designed for hotel groups and investors "
        "to manage performance across multiple properties."
    )


if __name__ == "__main__":
    main()

