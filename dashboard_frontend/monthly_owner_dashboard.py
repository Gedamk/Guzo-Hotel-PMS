# -*- coding: utf-8 -*-
"""
monthly_owner_dashboard.py – Monthly Owner / Investor View (v1.0)
-----------------------------------------------------------------
Streamlit dashboard built on top of:
    guzo_backend.modules.reports_monthly_owner.get_monthly_owner_report

Audience:
    • Hotel owners
    • Asset managers
    • Investors

Core KPIs (per property, per month):
    • Occupancy %
    • ADR (Average Daily Rate)
    • RevPAR
    • Room Revenue (ETB)
    • Room Nights Sold
    • Number of Bookings
    • Basic payment mix breakdown (if available)
"""

import datetime

import streamlit as st

from guzo_backend.modules.reports_monthly_owner import get_monthly_owner_report


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _current_year_month():
    today = datetime.date.today()
    return today.year, today.month


def _format_month(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


# ---------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Guzo – Monthly Owner Dashboard",
        layout="wide",
    )

    st.title("📊 Monthly Owner Dashboard")
    st.caption(
        "High-level performance snapshot for hotel owners and investors – "
        "powered by Guzo Guest Assist & Postgres."
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

    property_code = st.sidebar.text_input(
        "Property Code",
        value="DRE001",
        help="Use the hotel property code as stored in the `hotels` table (e.g., DRE001, N&N002).",
    )

    if st.sidebar.button("🔄 Refresh report"):
        st.experimental_rerun()

    # ---------------- Fetch report ----------------
    st.subheader(f"Summary for {_format_month(year, month)}")

    try:
        report = get_monthly_owner_report(
            year=year,
            month=month,
            property_code=property_code or None,
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
        # Expecting structure like:
        # {
        #   "💵 Cash": {"bookings": 2, "nights": 8, "revenue_etb": 48000},
        #   "Card": {...},
        #   ...
        # }
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
            import pandas as pd

            df_methods = pd.DataFrame(rows)
            st.dataframe(df_methods, use_container_width=True)

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
        import pandas as pd

        df_bookings = pd.DataFrame(example_bookings)
        st.dataframe(df_bookings, use_container_width=True)
    else:
        st.write("No sample bookings available in this report.")

    # ---------------- Footer ----------------
    st.caption(
        "Guzo Guest Assist – Monthly Owner View · Designed for hotel owners, "
        "investors, and asset managers to see performance at a glance."
    )


if __name__ == "__main__":
    main()
