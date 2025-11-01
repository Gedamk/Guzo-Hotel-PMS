# -*- coding: utf-8 -*-
"""
central_dashboard.py – Guzo Central Overview (v3.1)
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

from guzo_backend.modules import google_sheets, system_health


# ======================================================
# 🔄 Load Data
# ======================================================
def load_data():
    """Load hotel contacts from Google Sheets."""
    google_sheets.init_client()
    df = google_sheets.load_hotel_contacts()

    if isinstance(df, list):
        df = pd.DataFrame(df)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str)

    return df


# ======================================================
# 🧭 Main Dashboard
# ======================================================
def show_dashboard():
    st.set_page_config(
        page_title="Central Dashboard",
        layout="wide",
        page_icon="🌍",
    )

    st.title("🌍 Guzo Guest Assist – Central Operations Dashboard")
    st.caption("Real-time overview of all hotels, KPIs, and system health.")

    # --------------------------------------------------
    # Auto Refresh (every 120s)
    # --------------------------------------------------
    refresh_rate = 120
    st.sidebar.markdown("### 🔄 Auto Refresh")
    st.sidebar.caption(f"Page refreshes every {refresh_rate} seconds.")
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_rate}'>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------
    try:
        df = load_data()
        st.success(f"✅ Loaded {len(df)} hotel records successfully.")
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        return

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hotels", len(df))
    col2.metric(
        "Integrated",
        (df["Integration Status"] == "Active").sum()
        if "Integration Status" in df.columns
        else 0,
    )
    col3.metric(
        "Pending Setup",
        (df["Integration Status"] != "Active").sum()
        if "Integration Status" in df.columns
        else 0,
    )
    col4.metric("Last Sync", datetime.now().strftime("%Y-%m-%d %H:%M"))

    st.markdown("---")

    # --------------------------------------------------
    # Chart: Integration Status
    # --------------------------------------------------
    if "Integration Status" in df.columns:
        counts = df["Integration Status"].value_counts().reset_index()
        counts.columns = ["Status", "Count"]
        fig = px.pie(
            counts,
            names="Status",
            values="Count",
            title="Hotel Integration Status Overview",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    else:
        st.info("Integration status data not available.")

    st.markdown("---")

    # --------------------------------------------------
    # System Health Summary
    # --------------------------------------------------
    st.subheader("🩺 System Health Summary")
    try:
        health = system_health.get_status_summary()
        df_health = pd.DataFrame(list(health.items()), columns=["Component", "Status"])
        df_health["Indicator"] = df_health["Status"].apply(
            lambda s: "✅ OK" if s == "OK" else "❌ FAIL"
        )
        st.dataframe(df_health[["Component", "Indicator"]], width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"⚠️ Could not fetch system health summary: {e}")

    st.markdown("---")

    # --------------------------------------------------
    # Hotel Data Table
    # --------------------------------------------------
    st.subheader("🏨 Registered Hotels")
    st.dataframe(df, width="stretch", hide_index=True)

    # --------------------------------------------------
    # Export Options
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("💾 Export Options")
    colA, colB = st.columns(2)
    with colA:
        if st.button("📤 Export CSV"):
            csv = df.to_csv(index=False).encode("utf-8")
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
