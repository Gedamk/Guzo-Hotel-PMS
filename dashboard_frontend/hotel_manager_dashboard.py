# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Hotel Manager Dashboard (v2.5)
--------------------------------------------------
• Fixed Plotly deprecation warnings
• Added Multi-Hotel KPI Summary tab
• Safe auto-refresh + clean visualization
• UTF-8 + Streamlit ≥1.40 compliant
"""

import sys, os, time
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ✅ Add backend import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from guzo_backend.modules import google_sheets

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
# 🖼️ HEADER / LOGO
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
REFRESH_INTERVAL = 60
st.sidebar.markdown("### 🔄 Auto Refresh")
st.sidebar.caption(f"Refresh every {REFRESH_INTERVAL} seconds.")
st.sidebar.caption("Last refreshed: " + datetime.now().strftime("%H:%M:%S"))

# ======================================================
# 🧭 SIDEBAR INFO
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
# 📊 TAB NAVIGATION
# ======================================================
tabs = st.tabs(["🏢 Single Hotel Overview", "🌍 Multi-Hotel Summary"])

# ======================================================
# TAB 1 – SINGLE HOTEL OVERVIEW
# ======================================================
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    col1.metric("Integration Status",
                 hotel_df["Integration Status"].iloc[0] if not hotel_df.empty else "N/A")
    col2.metric("Language",
                 hotel_df["Preferred Language"].iloc[0]
                 if "Preferred Language" in hotel_df.columns else "N/A")
    col3.metric("Date", datetime.now().strftime("%B %d, %Y"))

    st.markdown("---")
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
                st.dataframe(df_logs.tail(20), use_container_width=True, height=380)
            else:
                st.info("No recent guest messages found.")
        else:
            st.warning("⚠️ Could not access notification logs.")
    except Exception as e:
        st.error(f"❌ Failed to load logs: {e}")
        df_logs = pd.DataFrame()

    st.markdown("---")
    st.subheader("📈 Performance Summary")

    try:
        summary = {
            "Total Guests This Week": 42,
            "Average Room Rate (ETB)": 3200,
            "Revenue (ETB)": 134400,
            "Pending Confirmations": 3,
        }
        df_summary = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        df_chart = pd.DataFrame({
            "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "Revenue": [20000, 22000, 21000, 19500, 24500, 26000, 27000],
            "Guests": [10, 12, 11, 9, 14, 15, 16],
        })

        t1, t2 = st.tabs(["💰 Revenue", "👥 Guests"])
        with t1:
            fig1 = px.line(df_chart, x="Day", y="Revenue", markers=True,
                           title="Daily Revenue Trend (ETB)")
            fig1.update_layout(template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig1, use_container_width=True, config={"displaylogo": False})
        with t2:
            fig2 = px.bar(df_chart, x="Day", y="Guests", text_auto=True,
                          title="Guest Count Trend")
            fig2.update_layout(template="plotly_white")
            st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False})
    except Exception as e:
        st.error(f"⚠️ Could not generate summary: {e}")

    # Export
    st.markdown("---")
    st.subheader("🧾 Export Reports")
    colA, colB = st.columns(2)
    with colA:
        if not df_logs.empty:
            csv = df_logs.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Logs (CSV)", data=csv,
                               file_name=f"{hotel_name}_Logs.csv", mime="text/csv")
        else:
            st.info("No logs available for export.")
    with colB:
        if st.button("🔄 Manual Refresh"):
            st.rerun()

# ======================================================
# TAB 2 – MULTI-HOTEL SUMMARY
# ======================================================
with tabs[1]:
    st.subheader("🌍 Multi-Hotel KPI Summary")

    try:
        df_multi = df_hotels[["Hotel Name", "City", "Manager Email", "Integration Status"]].copy()
        df_multi["Occupancy (%)"] = [68, 75, 80, 77, 70, 82][: len(df_multi)]
        df_multi["Revenue (ETB)"] = [120000, 150000, 180000, 160000, 140000, 200000][: len(df_multi)]
        df_multi["ADR (ETB)"] = [3000, 3200, 3500, 3300, 3100, 3700][: len(df_multi)]
        df_multi["RevPAR (ETB)"] = (df_multi["ADR (ETB)"] * df_multi["Occupancy (%)"] / 100).round(0)

        st.dataframe(df_multi, use_container_width=True, hide_index=True)

        st.markdown("#### 📊 KPI Comparison")
        fig_multi = px.bar(
            df_multi,
            x="Hotel Name",
            y="Revenue (ETB)",
            color="Occupancy (%)",
            text_auto=True,
            title="Hotel Revenue vs Occupancy Rate",
            color_continuous_scale="Blues"
        )
        fig_multi.update_layout(template="plotly_white", yaxis_title="Revenue (ETB)")
        st.plotly_chart(fig_multi, use_container_width=True, config={"displaylogo": False})

    except Exception as e:
        st.error(f"❌ Multi-Hotel Summary failed: {e}")

# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.caption("© 2025 Guzo Guest Assist | v2.5 | Developed by Gedam Kacha")
