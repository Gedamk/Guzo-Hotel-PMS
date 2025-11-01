# -*- coding: utf-8 -*-
"""
notification_logs.py – Guzo Guest Assist Dashboard Page (Final Unified Edition)
-------------------------------------------------------------------------------
Displays all Email / WhatsApp / SMS notifications sent to guests.
✅ Google Sheets as primary source
✅ SQLite as local fallback
✅ Unified visual style (same as Manager Center)
"""

import os
import sys
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from guzo_booking_bot.modules import google_sheets

# ======================================================
# 🌍 ENVIRONMENT SETUP
# ======================================================
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path=env_path, override=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ======================================================
# ⚙️ PAGE CONFIG
# ======================================================
st.set_page_config(page_title="📨 Notification Logs – Guzo Guest Assist", layout="wide")

# ======================================================
# 🌟 HEADER (Unified with Manager Center)
# ======================================================
st.markdown(
    """
    <div style="
        background-color:#004B8D;
        color:white;
        padding:1.5rem;
        border-radius:0.8rem;
        text-align:center;
        box-shadow:0 2px 6px rgba(0,0,0,0.2);
        font-family:'Helvetica Neue', sans-serif;">
        <h1 style="margin-bottom:0;">🏨 Guzo Guest Assist – Notification Logs</h1>
        <p style="margin-top:4px; font-size:15px; color:#FFB703;">
            ቆይታዎን እንረዳለን። — Your Stay, Our Assist.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================
# 🔄 AUTO REFRESH (every 45 seconds)
# ======================================================
st.markdown("<meta http-equiv='refresh' content='45'>", unsafe_allow_html=True)

# ======================================================
# 🧩 Load logs from Google Sheets
# ======================================================
st.subheader("☁️ Google Sheets Logs")

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
                "Filter by Channel",
                ["All"] + sorted(df["Channel"].dropna().unique().tolist()),
            )
            status_filter = col3.selectbox(
                "Filter by Status",
                ["All"] + sorted(df["Status"].dropna().unique().tolist()),
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
            st.warning("⚠️ No results found for selected filters.")
        else:
            st.dataframe(df, width="stretch", height=500)
    else:
        st.warning("⚠️ No connection to Google Sheets.")
        df = pd.DataFrame()
except Exception as e:
    st.error(f"❌ Failed to load from Google Sheets: {e}")
    df = pd.DataFrame()

# ======================================================
# 🗄️ Load fallback logs from local SQLite
# ======================================================
st.subheader("💾 Local Backup (SQLite Fallback)")

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
        st.write("ℹ️ No local fallback logs found.")
except Exception as e:
    st.error(f"⚠️ Error reading local logs: {e}")

# ======================================================
# 📊 Summary insights
# ======================================================
if "df" in locals() and df is not None and not df.empty:
    st.subheader("📊 Summary Insights")
    summary = (
        df.groupby(["Channel", "Status"])
        .size()
        .reset_index(name="Count")
    )
    st.dataframe(summary, width="stretch")
    st.markdown(
        f"<p style='text-align:center;color:gray;'>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        unsafe_allow_html=True,
    )
else:
    st.warning("⚠️ No data available yet — check your Google Sheet connection.")

# ======================================================
# 🌍 FOOTER
# ======================================================
st.markdown(
    """
    <hr style="margin-top:2rem; border:1px solid #FFB703;">
    <div style="text-align:center; color:#5C4033; font-size:13px;">
        <strong>Guzo Guest Assist</strong> | Addis Ababa, Ethiopia<br>
        <em>Empowering Ethiopian Hospitality with Global Technology</em><br>
        <span style="color:#007A33;">ቆይታዎን እንረዳለን። — Your Stay, Our Assist.</span><br><br>
        <small style="color:#999;">© 2025 Guzo Guest Assist | All rights reserved.</small>
    </div>
    """,
    unsafe_allow_html=True,
)
