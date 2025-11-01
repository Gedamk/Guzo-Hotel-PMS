# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Hotel Manager Dashboard (v2.3)
--------------------------------------------------
• UTF-8 clean
• Streamlit ≥1.40 compliant
• Auto-refresh every 60 seconds
• Live KPIs + Safe Plotly config
• Restored logo banner
"""

import sys, os, time
import streamlit as st
import pandas as pd
from datetime import datetime

# ✅ Parent import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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
# 🖼️ COMPANY LOGO / HEADER
# ======================================================
logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
col_logo, col_title = st.columns([0.15, 0.85])
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=60)
    else:
        st.markdown("<div style='font-size:40px;'>🏨</div>", unsafe_allow_html=True)
with col_title:
    st.title("Guzo Guest Assist – Manager Dashboard")
    st.caption("Your Stay, Our Assist | Powered by Guzo Systems")

# ======================================================
# 🔄 AUTO-REFRESH
# ======================================================
refresh_rate = 60  # seconds
st.sidebar.markdown("### 🔄 Auto Refresh")
st.sidebar.caption(f"Page refreshes every {refresh_rate} seconds.")
st.markdown(
    f"<meta http-equiv='refresh' content='{refresh_rate}'>",
    unsafe_allow_html=True,
)

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
    for col in df_hotels.columns:
        if df_hotels[col].dtype == "object":
            df_hotels[col] = df_hotels[col].fillna("").astype(str)
    hotel_df = df_hotels[df_hotels["Hotel Name"] == hotel_name]
    if hotel_df.empty:
        st.error("⚠️ Your hotel was not found in system records.")
    else:
        st.success(f"🏨 Connected to {hotel_name}")
except Exception as e:
    st.error(f"❌ Unable to load hotel data: {e}")
    hotel_df = pd.DataFrame()

# ======================================================
# 🏢 HOTEL OVERVIEW KPIs
# ======================================================
col1, col2, col3 = st.columns(3)
col1.metric("Integration Status",
             hotel_df["Integration Status"].iloc[0] if not hotel_df.empty else "N/A")
col2.metric("Language",
             hotel_df["Preferred Language"].iloc[0]
             if "Preferred Language" in hotel_df.columns else "N/A")
col3.metric("Date", datetime.now().strftime("%B %d, %Y"))
st.markdown("---")

# ======================================================
# 📬 GUEST COMMUNICATION LOG
# ======================================================
st.subheader("📬 Recent Guest Messages & Notifications")

try:
    logs_sheet = google_sheets._open_sheet(
        google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID, "Notifications Log"
    )
    if logs_sheet:
        df_logs = pd.DataFrame(logs_sheet.get_all_records())
        for c in df_logs.columns:
            df_logs[c] = df_logs[c].fillna("").astype(str)
        df_logs = df_logs[df_logs["Hotel Name"] == hotel_name]
        if not df_logs.empty:
            st.dataframe(df_logs.tail(20), width="stretch", height=400)
        else:
            st.info("No recent guest messages found.")
    else:
        st.warning("⚠️ Could not access notification logs.")
except Exception as e:
    st.error(f"❌ Failed to load logs: {e}")
    df_logs = pd.DataFrame()

# ======================================================
# 📈 PERFORMANCE SUMMARY
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
    st.dataframe(df_summary, width="stretch", hide_index=True)
except Exception as e:
    st.error(f"⚠️ Could not generate summary: {e}")

# ======================================================
# 🧾 EXPORT DATA
# ======================================================
st.markdown("---")
st.subheader("🧾 Export Reports")

colA, colB = st.columns(2)
with colA:
    if st.button("📤 Download Logs (CSV)"):
        try:
            if not df_logs.empty:
                csv = df_logs.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Save CSV File",
                    csv,
                    file_name=f"{hotel_name}_Logs.csv",
                    mime="text/csv",
                )
            else:
                st.warning("⚠️ No logs available for download.")
        except Exception as e:
            st.error(f"⚠️ Export failed: {e}")

with colB:
    if st.button("🔄 Manual Refresh"):
        st.rerun()

st.markdown("---")
st.caption(
    "© 2025 Guzo Guest Assist | Hotel Manager Dashboard | Developed by Gedam Kacha"
)
