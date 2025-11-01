# -*- coding: utf-8 -*-
"""
Notification Logs Dashboard Page
--------------------------------
Displays all email / WhatsApp / SMS notifications sent to guests.
Pulls from Google Sheets or local SQLite fallback.
"""
# ✅ Force load the .env file correctly
from dotenv import load_dotenv
import os

env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path=env_path, override=True)

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from guzo_backend.modules import google_sheets
# --- Streamlit Compatibility Fix (for newer versions) ---
import streamlit as st

# Monkey patch to safely ignore deprecated 'use_container_width' calls
if not hasattr(st.dataframe, "_patched"):
    _old_dataframe = st.dataframe
    def _patched_dataframe(*args, **kwargs):
        if "use_container_width" in kwargs:
            kwargs.pop("use_container_width")
            kwargs["width"] = "stretch"
        return _old_dataframe(*args, **kwargs)
    st.dataframe = _patched_dataframe
    st.dataframe._patched = True

# ======================================================
# ⚙️ PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Notification Logs", layout="wide")

# ======================================================
# 🔄 AUTO REFRESH (every 45 seconds)
# ======================================================
st_autorefresh = st.empty()
st_autorefresh.markdown(
    "<meta http-equiv='refresh' content='45'>", unsafe_allow_html=True
)

st.title("📨 Notification Logs – Guzo Guest Assist")

# ======================================================
# 🧩 Load logs from Google Sheets
# ======================================================
st.subheader("Google Sheets Logs")

try:
    logs = google_sheets._open_sheet(
        google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
    )
    if logs:
        data = logs.get_all_records()
        df = pd.DataFrame(data)
        st.success(f"✅ Loaded {len(df)} logs from Google Sheets")

        # ===========================================
        # 🔍 FILTERS & SEARCH BAR
        # ===========================================
        with st.expander("🔎 Filter Options", expanded=True):
            col1, col2, col3 = st.columns(3)
            guest_filter = col1.text_input("Search Guest Name")
            channel_filter = col2.selectbox(
                "Filter by Channel", ["All"] + sorted(df["Channel"].dropna().unique().tolist())
            )
            status_filter = col3.selectbox(
                "Filter by Status", ["All"] + sorted(df["Status"].dropna().unique().tolist())
            )

        # Apply filters
        if guest_filter:
            df = df[df["Guest Name"].str.contains(guest_filter, case=False, na=False)]
        if channel_filter != "All":
            df = df[df["Channel"] == channel_filter]
        if status_filter != "All":
            df = df[df["Status"] == status_filter]

        # ===========================================
        # 📋 Display filtered data
        # ===========================================
        if df.empty:
            st.warning("No results found for selected filters.")
        else:
            st.dataframe(df, width="stretch", height=500)
    else:
        st.warning("⚠️ No connection to Google Sheets.")
except Exception as e:
    st.error(f"❌ Failed to load from Google Sheets: {e}")
    df = pd.DataFrame()

# ======================================================
# 🗄️ Load fallback logs from local SQLite
# ======================================================
st.subheader("Local Backup (SQLite Fallback)")

try:
    local_db = os.path.join("storage", "logs.db")
    if os.path.exists(local_db):
        conn = sqlite3.connect(local_db)
        local_df = pd.read_sql_query("SELECT * FROM failed_logs ORDER BY id DESC", conn)
        conn.close()

        st.info(f"💾 {len(local_df)} offline logs stored locally.")
        st.dataframe(local_df, width="stretch", height=400)

        if st.button("🧹 Clear Local Logs"):
            conn = sqlite3.connect(local_db)
            conn.execute("DELETE FROM failed_logs")
            conn.commit()
            conn.close()
            st.success("✅ Local logs cleared successfully.")
    else:
        st.write("No local fallback logs found.")
except Exception as e:
    st.error(f"⚠️ Error reading local logs: {e}")

# ======================================================
# 📊 Summary insights
# ======================================================

if 'df' in locals() and df is not None and not df.empty:
    st.subheader("Summary Insights")
    summary = (
        df.groupby(["Channel", "Status"])
        .size()
        .reset_index(name="Count")
    )
    st.dataframe(summary)
else:
    st.warning("⚠️ No data available yet — check your Google Sheet connection.")
