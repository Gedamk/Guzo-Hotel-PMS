# -*- coding: utf-8 -*-
"""
sidebar.py – Navigation Sidebar for Guzo Dashboard
---------------------------------------------------
Provides sidebar navigation and app info.
UTF-8 clean and Streamlit 1.40+ compatible.
"""

import streamlit as st
from datetime import datetime


def show_sidebar():
    """Builds the sidebar UI and returns the selected page."""
    st.sidebar.title("🧭 Guzo Dashboard")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Select a page:",
        ["🏠 Home (Launcher)", "📊 Central Dashboard", "🧾 Notification Logs"],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Controls")
    if st.sidebar.button("🔄 Refresh Data"):
        st.toast("Reloading data, please wait...")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"🕒 Last opened: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    st.sidebar.caption("© 2025 Guzo Guest Assist")

    return page
