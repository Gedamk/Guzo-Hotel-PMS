# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Hotel Manager / Central Dashboard (v3.0)
------------------------------------------------------------
• Central Control Center for Guzo Guest Assist
• Owner & Hotel reports (single + multi-hotel)
• Embedded React KPI dashboard (portfolio + live bookings)
• System Health section
• UTF-8 clean and Streamlit ≥1.40 compatible for st.dataframe
"""

import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# ======================================================
# PYTHON PATH – allow importing guzo_backend.*
# ======================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from guzo_backend.modules.auth_simple import require_role  # noqa: E402
from guzo_backend.modules import google_sheets  # noqa: E402
from components.system_health import render_system_status  # noqa: E402

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Guzo Guest Assist – Central Dashboard",
    page_icon="🏨",
    layout="wide",
)

# ======================================================
# ROLE / AUTH – Central Control Center
# ======================================================
auth = require_role(["central_admin", "portfolio_owner", "hotel_owner"])
role = auth.get("role", "unknown")
allowed_properties = auth.get("allowed_properties", [])

# Session-based identity (for hotel-specific info, if present)
hotel_name = st.session_state.get("hotel_name", "Unknown Hotel")
manager_email = st.session_state.get("user", "Unknown User")

# ======================================================
# HEADER / LOGO
# ======================================================
logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
col_logo, col_title = st.columns([0.15, 0.85])

with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=60)
    else:
        st.markdown("<div style='font-size:40px;'>🏨</div>", unsafe_allow_html=True)

with col_title:
    st.title("Guzo Guest Assist – Central Control Center")
    st.caption("Your Stay, Our Assist | Powered by Guzo Systems")

# ======================================================
# SIDEBAR – ROLE, NAVIGATION, AUTO-REFRESH
# ======================================================
with st.sidebar:
    st.markdown("### 👤 Current User")
    st.write(f"**Role:** {role}")
    if allowed_properties:
        st.write("**Allowed Properties:**")
        for code in allowed_properties:
            st.write(f"- `{code}`")
    else:
        st.write("No properties assigned (local dev).")

    st.markdown("---")
    st.title(f"🏨 {hotel_name}")
    st.markdown(f"👤 **Manager:** {manager_email}")

    # Auto-refresh display (informational, not a timer)
    REFRESH_INTERVAL = 60
    st.markdown("### 🔄 Auto Refresh")
    st.caption(f"Recommended: refresh every {REFRESH_INTERVAL} seconds.")
    st.caption("Last loaded: " + datetime.now().strftime("%H:%M:%S"))

    if st.button("🔒 Logout"):
        st.session_state.clear()
        st.success("You have been logged out. Close this tab or go back to login.")
        st.stop()

    st.markdown("---")
    st.caption("Hotel & Portfolio Dashboard – Guzo Guest Assist")

    # Section navigation
    section = st.radio(
        "Go to section:",
        [
            "📊 Business KPIs (React)",
            "📈 Owner & Hotel Reports",
            "🩺 System Health",
            "🔔 Notifications Log",
        ],
    )

# ======================================================
# SHEETS / DATA INITIALIZATION
# ======================================================
df_hotels: pd.DataFrame = pd.DataFrame()
hotel_df: pd.DataFrame = pd.DataFrame()

try:
    google_sheets.init_client()
    st.sidebar.success("✅ Connected to Google Sheets (or safe fallback)")
except Exception as e:
    st.sidebar.error(f"❌ Sheets connection failed: {e}")

try:
    df_hotels = google_sheets.load_hotel_contacts()
    if isinstance(df_hotels, list):
        df_hotels = pd.DataFrame(df_hotels)

    # Normalize text columns
    for col in df_hotels.columns:
        if df_hotels[col].dtype == "object":
            df_hotels[col] = df_hotels[col].fillna("").astype(str)

    # Filter to current hotel (from session)
    hotel_df = df_hotels[df_hotels["Hotel Name"] == hotel_name]

    if hotel_df.empty:
        st.warning("⚠️ Your hotel was not found in system records (using static or fallback data).")
    else:
        st.success(f"🏨 Connected to {hotel_name}")
except Exception as e:
    st.error(f"❌ Unable to load hotel data: {e}")
    df_hotels = pd.DataFrame()
    hotel_df = pd.DataFrame()

# ======================================================
# SECTION 1 – BUSINESS KPIs (React dashboard_ui)
# ======================================================
if section == "📊 Business KPIs (React)":
    st.subheader("📊 Portfolio & Live Bookings (React Dashboard)")
    st.info(
        "This view is powered by the React app in `dashboard_ui`, "
        "calling the FastAPI endpoints `/reports/portfolio`, `/reports/hotel`, and `/bookings`."
    )
    components.iframe("http://localhost:3000", height=900)

# ======================================================
# SECTION 2 – OWNER & HOTEL REPORTS (Streamlit)
# ======================================================
if section == "📈 Owner & Hotel Reports":
    st.subheader("📈 Owner & Hotel Reports")

    # Tabs: Single hotel vs multi-hotel
    tabs = st.tabs(["🏢 Single Hotel Overview", "🌍 Multi-Hotel Summary"])

    # ----------------------------
    # TAB 1 – SINGLE HOTEL OVERVIEW
    # ----------------------------
    with tabs[0]:
        col1, col2, col3 = st.columns(3)

        integration_status = (
            hotel_df["Integration Status"].iloc[0]
            if not hotel_df.empty and "Integration Status" in hotel_df.columns
            else "N/A"
        )
        preferred_language = (
            hotel_df["Preferred Language"].iloc[0]
            if not hotel_df.empty and "Preferred Language" in hotel_df.columns
            else "N/A"
        )

        col1.metric("Integration Status", integration_status)
        col2.metric("Language", preferred_language)
        col3.metric("Date", datetime.now().strftime("%B %d, %Y"))

        st.markdown("---")
        st.subheader("📬 Recent Guest Messages & Notifications")

        df_logs: pd.DataFrame = pd.DataFrame()

        try:
            # Legacy helper uses internal ID and sheet name
            logs_sheet = google_sheets._open_sheet(
                google_sheets.SPREADSHEET_NOTIFICATIONSLOG_ID,
                "Notifications Log",
            )
            if logs_sheet:
                df_logs = pd.DataFrame(logs_sheet.get_all_records())
                for c in df_logs.columns:
                    df_logs[c] = df_logs[c].fillna("").astype(str)
                df_logs = df_logs[df_logs.get("Hotel Name", "") == hotel_name]

                if not df_logs.empty:
                    st.dataframe(
                        df_logs.tail(20),
                        width="stretch",
                        height=380,
                    )
                else:
                    st.info("No recent guest messages found for this hotel.")
            else:
                st.warning("⚠️ Could not access notification logs (Sheets client not available).")
        except Exception as e:
            st.error(f"❌ Failed to load notification logs: {e}")
            df_logs = pd.DataFrame()

        st.markdown("---")
        st.subheader("📈 Performance Summary (sample data for layout)")

        try:
            # Sample metrics – replace with real DB/booking aggregates later
            summary = {
                "Total Guests This Week": 42,
                "Average Room Rate (ETB)": 3200,
                "Revenue (ETB)": 134_400,
                "Pending Confirmations": 3,
            }
            df_summary = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
            st.dataframe(df_summary, width="stretch")

            df_chart = pd.DataFrame(
                {
                    "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "Revenue": [20000, 22000, 21000, 19500, 24500, 26000, 27000],
                    "Guests": [10, 12, 11, 9, 14, 15, 16],
                }
            )

            t1, t2 = st.tabs(["💰 Revenue", "👥 Guests"])

            with t1:
                fig1 = px.line(
                    df_chart,
                    x="Day",
                    y="Revenue",
                    markers=True,
                    title="Daily Revenue Trend (ETB)",
                )
                fig1.update_layout(template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig1, use_container_width=True, config={"displaylogo": False})

            with t2:
                fig2 = px.bar(
                    df_chart,
                    x="Day",
                    y="Guests",
                    text_auto=True,
                    title="Guest Count Trend",
                )
                fig2.update_layout(template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False})

        except Exception as e:
            st.error(f"⚠️ Could not generate performance summary: {e}")

        st.markdown("---")
        st.subheader("🧾 Export Reports")

        colA, colB = st.columns(2)
        with colA:
            if not df_logs.empty:
                csv = df_logs.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Notification Logs (CSV)",
                    data=csv,
                    file_name=f"{hotel_name}_Notifications.csv",
                    mime="text/csv",
                )
            else:
                st.info("No logs available for export.")

        with colB:
            if st.button("🔄 Manual Refresh"):
                st.rerun()

    # ----------------------------
    # TAB 2 – MULTI-HOTEL SUMMARY
    # ----------------------------
    with tabs[1]:
        st.subheader("🌍 Multi-Hotel KPI Summary (sample layout)")

        try:
            if df_hotels.empty:
                st.info("No hotel list available (static fallback not loaded).")
            else:
                df_multi = df_hotels.copy()
                # Keep only key columns that usually exist
                keep_cols = ["Hotel Name", "City", "Manager Email", "Integration Status"]
                df_multi = df_multi[[c for c in keep_cols if c in df_multi.columns]]

                # Sample numeric KPIs – replace with real aggregated numbers from DB later
                n = len(df_multi)
                df_multi["Occupancy (%)"] = [68, 75, 80, 77, 70, 82][:n]
                df_multi["Revenue (ETB)"] = [120000, 150000, 180000, 160000, 140000, 200000][:n]
                df_multi["ADR (ETB)"] = [3000, 3200, 3500, 3300, 3100, 3700][:n]
                df_multi["RevPAR (ETB)"] = (
                    df_multi["ADR (ETB)"] * df_multi["Occupancy (%)"] / 100
                ).round(0)

                st.dataframe(df_multi, width="stretch")

                st.markdown("#### 📊 KPI Comparison")

                fig_multi = px.bar(
                    df_multi,
                    x="Hotel Name",
                    y="Revenue (ETB)",
                    color="Occupancy (%)",
                    text_auto=True,
                    title="Hotel Revenue vs Occupancy Rate",
                )
                fig_multi.update_layout(template="plotly_white", yaxis_title="Revenue (ETB)")
                st.plotly_chart(fig_multi, use_container_width=True, config={"displaylogo": False})

        except Exception as e:
            st.error(f"❌ Multi-Hotel Summary failed: {e}")

# ======================================================
# SECTION 3 – SYSTEM HEALTH
# ======================================================
if section == "🩺 System Health":
    st.subheader("🩺 System Health Monitor")
    render_system_status()

# ======================================================
# SECTION 4 – NOTIFICATIONS LOG (GLOBAL VIEW – PLACEHOLDER)
# ======================================================
if section == "🔔 Notifications Log":
    st.subheader("🔔 Notifications Log (Portfolio View)")
    st.info(
        "In the current environment, Google Sheets is disabled and this view "
        "may be empty. In the next step, this will be connected to a PostgreSQL "
        "notifications table for all properties."
    )

    # Example placeholder: show that the module is reachable
    try:
        # If you later create a DB-backed notifications loader, call it here.
        st.write("No unified notifications source configured yet.")
    except Exception as e:
        st.error(f"❌ Failed to load portfolio notifications: {e}")

# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.caption("© 2025 Guzo Guest Assist | Central Dashboard v3.0 | Developed by Gedam Kacha")
