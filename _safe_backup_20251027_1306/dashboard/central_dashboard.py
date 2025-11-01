# -*- coding: utf-8 -*-
"""
central_dashboard.py – Guzo Central Overview
--------------------------------------------
Displays aggregated KPIs, hotel summaries, and real-time metrics.
Fully UTF-8 safe and compatible with Streamlit >=1.40.
"""

import sys
import os
from datetime import datetime
import streamlit as st

# ✅ Import fix for parent modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_booking_bot.modules import google_sheets


def load_data():
    """Load hotel contacts and clean dataframe."""
    google_sheets.init_client()
    df = google_sheets.load_hotel_contacts()

    # 🧹 Clean data
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str)

    return df


def show_dashboard():
    st.set_page_config(
        page_title="Central Dashboard",
        layout="wide",
        page_icon="📊",
    )

    st.title("📊 Central Operations Dashboard")
    st.caption("Live overview of Guzo Guest Assist hotels and key metrics.")

    try:
        df = load_data()
        st.success(f"✅ Loaded {len(df)} hotel records successfully.")

        # Example KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Hotels", len(df))
        col2.metric("Active Telegram IDs", df["Telegram Chat ID"].astype(bool).sum())
        col3.metric("Last Sync", datetime.now().strftime("%H:%M:%S"))

        st.dataframe(df, width="stretch")

    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")


if __name__ == "__main__":
    show_dashboard()
