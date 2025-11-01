import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Hotel Manager Dashboard (v2.0)
--------------------------------------------------
Dedicated dashboard for individual hotel managers.
Automatically filters the manager’s property based on login credentials.
Allows access to guest messages, booking stats, and notifications.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from guzo_booking_bot.modules import google_sheets

# ======================================================
# 🛡️ SESSION VALIDATION
# ======================================================
if "role" not in st.session_state or st.session_state["role"] != "manager":
    st.warning("⚠️ Hotel Manager access only. Please log in.")
    st.switch_page("pages/login.py")

# ======================================================
# ⚙️ PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Guzo Guest Assist – Hotel Dashboard",
    page_icon="🏨",
    layout="wide",
)

hotel_name = st.session_state.get("hotel_name", "Unknown Hotel")
manager_email = st.session_state.get("user", "Unknown User")

# ======================================================
# 🧭 SIDEBAR CONTROL
# ======================================================
st.sidebar.title(f"🏨 {hotel_name}")
st.sidebar.markdown(f"👤 **Manager:** {manager_email}")

if st.sidebar.button("🔒 Logout"):
    st.session_state.clear()
    st.switch_page("pages/login.py")

st.sidebar.markdown("---")
st.sidebar.caption("Hotel Dashboard – Guzo Guest Assist")

# ======================================================
# 🔗 SYSTEM INITIALIZATION
# ======================================================
try:
    google_sheets.init_client()
    st.sidebar.success("✅ Connected to Google Sheets")
except Exception as e:
    st.sidebar.error(f"❌ Sheets connection failed: {e}")

# ======================================================
# 📋 LOAD HOTEL DATA
# ======================================================
try:
    df_hotels = google_sheets.load_hotel_contacts()
    if isinstance(df_hotels, list):
        df_hotels = pd.DataFrame(df_hotels)

    # Filter this manager’s hotel data only
    hotel_df = df_hotels[df_hotels["Hotel Name"] == hotel_name]
    if hotel_df.empty:
        st.error("⚠️ Your hotel was not found in the system records.")
    else:
        st.success(f"🏨 Connected to {hotel_name}")
except Exception as e:
    st.error(f"❌ Unable to load hotel data: {e}")
    hotel_df = pd.DataFrame()

# ======================================================
# 🏢 HOTEL OVERVIEW
# ======================================================
st.title(f"🏨 {hotel_name} – Manager Dashboard")
st.caption("Monitor your hotel’s guests, notifications, and booking performance.")

col1, col2, col3 = st.columns(3)
col1.metric("Integration Status", hotel_df["Integration Status"].iloc[0] if not hotel_df.empty else "N/A")
col2.metric("Language", hotel_df["Preferred Language"].iloc[0] if "Preferred Language" in hotel_df.columns else "N/A")
col3.metric("Date", datetime.now().strftime("%B %d, %Y"))

st.markdown("---")

# ======================================================
# 📬 GUEST COMMUNICATION LOG (Google Sheets)
# ======================================================
st.subheader("📬 Recent Guest Messages & Notifications")

try:
    logs = google_sheets._open_sheet(
        google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID,
        "Notifications Log"
    )

    if logs:
        data = logs.get_all_records()
        df_logs = pd.DataFrame(data)

        # Filter only this hotel’s messages
        df_logs = df_logs[df_logs["Hotel Name"] == hotel_name]

        if not df_logs.empty:
            st.dataframe(df_logs.tail(20), width="stretch", height=400)
        else:
            st.info("No recent guest messages found for this property.")
    else:
        st.warning("⚠️ Could not access notification logs.")
except Exception as e:
    st.error(f"❌ Failed to load logs: {e}")

# ======================================================
# 📈 PERFORMANCE SUMMARY (Optional future feature)
# ======================================================
st.markdown("---")
st.subheader("📊 Performance Summary")

try:
    summary = {
        "Total Guests This Week": 42,
        "Average Room Rate (ETB)": "3,200",
        "Revenue (ETB)": "134,400",
        "Pending Confirmations": 3,
    }

    df_summary = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
    st.table(df_summary)

except Exception as e:
    st.error(f"⚠️ Could not generate summary: {e}")

# ======================================================
# 🧾 EXPORT DATA
# ======================================================
st.markdown("---")
st.subheader("🧾 Export Reports")

colA, colB = st.columns(2)
if colA.button("📤 Download Logs (CSV)"):
    try:
        csv = df_logs.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Save CSV File", csv, f"{hotel_name}_Logs.csv", "text/csv")
    except Exception:
        st.warning("⚠️ No logs available for download.")
if colB.button("🔄 Refresh Data"):
    st.rerun()

st.markdown("---")
st.caption("© 2025 Guzo Guest Assist | Hotel Manager Dashboard | Developed by Gedam Kacha")
