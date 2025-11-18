# -*- coding: utf-8 -*-
"""
central_dashboard.py – Guzo Central Overview (v3.2)
---------------------------------------------------
Displays aggregated KPIs, hotel summaries, and system health metrics.
Streamlit ≥1.40 compliant and UTF-8 clean.
"""

import sys
import os
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

# ✅ Import fix for parent modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from guzo_backend.modules import google_sheets, system_health  # noqa

# --------------------------------------------------
# Streamlit page config must be first call
# --------------------------------------------------
st.set_page_config(page_title="Central Dashboard", layout="wide", page_icon="🌍")


def safe_plotly(fig):
    """Render Plotly chart with Streamlit deprecation-safe args."""
    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["toImage", "lasso2d", "select2d", "zoomIn2d", "zoomOut2d"],
            "responsive": True,
        },
    )


# ======================================================
# 🔄 Load Data
# ======================================================
def load_data() -> pd.DataFrame:
    """Load hotel contacts from Google Sheets safely."""
    # Initialize client (for clearer logs)
    google_sheets.init_client()

    df = google_sheets.load_hotel_contacts()
    if isinstance(df, list):
        df = pd.DataFrame(df)

    if df is None:
        return pd.DataFrame()

    # Normalize object columns
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str)

    return df


# ======================================================
# 🧭 Main Dashboard
# ======================================================
def show_dashboard():
    st.title("🌍 Guzo Guest Assist – Central Operations Dashboard")
    st.caption("Real-time overview of all hotels, KPIs, and system health.")

    # --------------------------------------------------
    # Auto Refresh (every 120s)
    # --------------------------------------------------
    refresh_rate = 120
    st.sidebar.markdown("### 🔄 Auto Refresh")
    st.sidebar.caption(f"Page refreshes every {refresh_rate} seconds.")
    st.markdown(f"<meta http-equiv='refresh' content='{refresh_rate}'>", unsafe_allow_html=True)

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------
    try:
        hotels_df = load_data()
        st.success(f"✅ Loaded {len(hotels_df)} hotel records successfully.")
    except Exception as e:
        st.error(f"❌ Dashboard Error loading hotels: {e}")
        hotels_df = pd.DataFrame()

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------
    total_hotels = len(hotels_df)
    integrated = 0
    pending = 0
    if not hotels_df.empty and "Integration Status" in hotels_df.columns:
        integrated = (hotels_df["Integration Status"].astype(str).str.lower() == "active").sum()
        pending = total_hotels - integrated

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Hotels", total_hotels)
    c2.metric("Integrated", integrated)
    c3.metric("Pending Setup", pending)
    c4.metric("Last Sync", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.markdown("---")

    # --------------------------------------------------
    # Chart: Integration Status
    # --------------------------------------------------
    if not hotels_df.empty and "Integration Status" in hotels_df.columns:
        counts = (
            hotels_df["Integration Status"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .reset_index()
        )
        counts.columns = ["Status", "Count"]
        if not counts.empty:
            fig = px.pie(
                counts,
                names="Status",
                values="Count",
                title="Hotel Integration Status Overview",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            safe_plotly(fig)
        else:
            st.info("No integration-status data to chart.")
    else:
        st.info("Integration status data not available.")

    st.markdown("---")

    # --------------------------------------------------
    # System Health Summary (fully guarded)
    # --------------------------------------------------
    st.subheader("🩺 System Health Summary")
    try:
        health = system_health.get_status_summary()
        if isinstance(health, dict) and health:
            df_health = pd.DataFrame(list(health.items()), columns=["Component", "Status"])
            df_health["Indicator"] = df_health["Status"].apply(
                lambda s: "✅ OK" if str(s).upper() == "OK" else "❌ FAIL"
            )
            st.dataframe(
                df_health[["Component", "Indicator"]],
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No system health data returned.")
    except Exception as e:
        st.warning(f"Could not fetch system health summary: {e}")

    st.markdown("---")

    # --------------------------------------------------
    # Hotel Data Table
    # --------------------------------------------------
    st.subheader("🏨 Registered Hotels")
    if not hotels_df.empty:
        st.dataframe(hotels_df, width="stretch", hide_index=True)
    else:
        st.info("No hotel records found yet.")

    # --------------------------------------------------
    # Export Options
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("💾 Export Options")
    colA, colB = st.columns(2)
    with colA:
        csv = hotels_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Save CSV File",
            csv,
            file_name=f"Hotel_List_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    with colB:
        if st.button("🔄 Manual Refresh"):
            st.rerun()

    st.markdown("---")
    st.caption("© 2025 Guzo Guest Assist | Central Dashboard | Developed by Gedam Kacha")


# ======================================================
# 🚀 Run App
# ======================================================
if __name__ == "__main__":
    show_dashboard()
