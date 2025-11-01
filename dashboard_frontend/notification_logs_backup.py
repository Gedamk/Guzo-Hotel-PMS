# -*- coding: utf-8 -*-
"""
Guzo Guest Assist â Notification Logs Dashboard (v2.0)
------------------------------------------------------
Displays all email / WhatsApp / SMS notifications sent to guests.
Includes role-based login security and Google Sheets + SQLite fallback.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from guzo_backend.modules import google_sheets

# ======================================================
# í´ SESSION SECURITY (Admin / Manager)
# ======================================================
if "role" not in st.session_state:
    st.warning("í´ Please log in first.")
    st.stop()

st.sidebar.markdown(f"í±¤ Logged in as: {st.session_state.get('user', 'Unknown')}")
if st.sidebar.button("í´ Logout"):
    st.session_state.clear()
    st.rerun()

# ======================================================
# âï¸ PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Notification Logs", layout="wide")
st.title("í³¨ Notification Logs â Guzo Guest Assist")
st.caption("Live multi-channel notification history for hotels and admin.")

# ======================================================
# ï¿½ï¿½ AUTO REFRESH (every 45 seconds)
# ======================================================
st.markdown("<meta http-equiv='refresh' content='45'>", unsafe_allow_html=True)

# ======================================================
# âï¸ LOAD LOGS FROM GOOGLE SHEETS
# ======================================================
st.subheader("âï¸ Google Sheets Logs")

try:
    logs = google_sheets._open_sheet(
        google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
    )
    if logs:
        data = logs.get_all_records()
        df = pd.DataFrame(data)
        st.success(f"â Loaded {len(df)} logs from Google Sheets")

        # ---------------------------
        # í´ FILTERS
        # ---------------------------
        with st.expander("í´ Filter Options", expanded=True):
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

        # ---------------------------
        # í³ DISPLAY DATA
        # ---------------------------
        if df.empty:
            st.warning("No results found for selected filters.")
        else:
            st.dataframe(df, width="stretch", height=500)
    else:
        st.warning("â ï¸ No connection to Google Sheets.")
except Exception as e:
    st.error(f"â Failed to load from Google Sheets: {e}")
    df = pd.DataFrame()

# ======================================================
# í·ï¸ LOCAL SQLITE FALLBACK
# ======================================================
st.subheader("í·ï¸ Local Backup (SQLite Fallback)")

try:
    local_db = os.path.join("storage", "logs.db")
    if os.path.exists(local_db):
        conn = sqlite3.connect(local_db)
        local_df = pd.read_sql_query("SELECT * FROM failed_logs ORDER BY id DESC", conn)
        conn.close()

        st.info(f"í²¾ {len(local_df)} offline logs stored locally.")
        st.dataframe(local_df, width="stretch", height=400)

        if st.button("í·¹ Clear Local Logs"):
            conn = sqlite3.connect(local_db)
            conn.execute("DELETE FROM failed_logs")
            conn.commit()
            conn.close()
            st.success("â Local logs cleared successfully.")
    else:
        st.write("No local fallback logs found.")
except Exception as e:
    st.error(f"â ï¸ Error reading local logs: {e}")

# ======================================================
# í³ SUMMARY INSIGHTS
# ======================================================
if "df" in locals() and df is not None and not df.empty:
    st.subheader("í³ Summary Insights")
    summary = (
        df.groupby(["Channel", "Status"])
        .size()
        .reset_index(name="Count")
    )
    st.dataframe(summary, width="stretch")
else:
    st.warning("â ï¸ No data available yet â check your Google Sheet connection.")
