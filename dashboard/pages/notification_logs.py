# -*- coding: utf-8 -*-
"""
Notification Logs Dashboard Page
--------------------------------
Displays all email / WhatsApp / SMS notifications sent to guests.
Now includes smart fallback to local SQLite backup when Google Sheets fails.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from guzo_booking_bot.modules import google_sheets

st.set_page_config(page_title="Notification Logs", layout="wide")

# ======================================================
# 🔄 Auto-refresh every 45 seconds
# ======================================================
st_autorefresh = st.empty()
st_autorefresh.markdown(
    "<meta http-equiv='refresh' content='45'>", unsafe_allow_html=True
)

st.title("📨 Notification Logs – Guzo Guest Assist")
st.caption("Automatically synced with Google Sheets, with local backup fallback.")

# ======================================================
# 🧩 Load from Google Sheets (Primary)
# ======================================================
@st.cache_data(ttl=120)
def load_from_google_sheets():
    try:
        sheet = google_sheets._open_sheet(
            google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
        )
        if sheet:
            records = sheet.get_all_records()
            return pd.DataFrame(records)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Google Sheets unavailable: {e}")
        return pd.DataFrame()

# ======================================================
# 🗄️ Load from SQLite (Fallback)
# ======================================================
def load_from_sqlite():
    db_path = os.path.join("storage", "logs.db")
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM notifications_backup ORDER BY id DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"⚠️ Local DB read failed: {e}")
        return pd.DataFrame()

# ======================================================
# 📊 Load and merge data
# ======================================================
google_df = load_from_google_sheets()
if not google_df.empty:
    st.success(f"✅ Loaded {len(google_df)} records from Google Sheets.")
    df = google_df
else:
    st.warning("⚠️ Google Sheets unreachable — loading from local backup.")
    df = load_from_sqlite()
    if not df.empty:
        st.info(f"💾 Showing {len(df)} records from local storage/logs.db.")
    else:
        st.error("❌ No data available in backup or online sources.")
        st.stop()

# ======================================================
# 📋 Display Table
# ======================================================
st.dataframe(df, use_container_width=True)

# ======================================================
# 📈 Summary Insights
# ======================================================
if not df.empty:
    st.markdown("---")
    st.subheader("📊 Message Channel Summary")
    if "Lang" in df.columns:
        summary = df.groupby(["Lang"]).size().reset_index(name="Count")
        st.bar_chart(summary, x="Lang", y="Count")

# ======================================================
# 🧹 Maintenance Tools
# ======================================================
st.markdown("---")
st.subheader("🧰 Maintenance Tools")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.success("✅ Data cache cleared — refreshing now.")
    st.rerun()

if st.button("🧹 Clear Local Backup"):
    db_path = os.path.join("storage", "logs.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM notifications_backup")
        conn.commit()
        conn.close()
        st.success("✅ Local logs cleared successfully.")
    else:
        st.warning("⚠️ No local backup file found.")

