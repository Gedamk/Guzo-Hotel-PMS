# -*- coding: utf-8 -*-
"""
notification_logs_dashboard.py – Notification & Logs Panel
----------------------------------------------------------
Displays logs of messages, alerts, and system status updates.
Fully UTF-8 safe and Streamlit >=1.40 compliant.
"""

import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime

# ✅ Ensure parent modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_backend.modules import log_helper


def load_logs():
    """Load notification logs if available."""
    try:
        df = log_helper.load_recent_logs(limit=200)
        # 🧹 Clean and standardize data
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=["Timestamp", "Level", "Message"])


def show_notification_logs():
    st.set_page_config(
        page_title="Notification Logs",
        layout="wide",
        page_icon="🧾",
    )

    st.title("🧾 Notification & System Logs")
    st.caption("Recent Telegram, Email, and System events.")

    df = load_logs()
    if df.empty:
        st.warning("No recent logs found.")
    else:
        st.success(f"✅ Loaded {len(df)} log entries.")
        st.dataframe(df, width="stretch")

    st.markdown("---")
    st.write(f"🕒 **Last refreshed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    show_notification_logs()
