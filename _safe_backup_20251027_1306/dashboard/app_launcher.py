# -*- coding: utf-8 -*-
"""
app_launcher.py – Guzo Guest Assist Dashboard (Executive Final Version)
-----------------------------------------------------------------------
Branded Streamlit dashboard with:
• UTF-8-safe encoding
• Sidebar + Top Banner + Summary KPIs
• Secure Google Sheets integration
• Streamlit ≥ 1.40 compliant (width="stretch")
"""

import sys, os
from datetime import datetime
import streamlit as st

# Allow parent imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_booking_bot.modules import google_sheets
from dashboard.sidebar import show_sidebar


# ╭────────────────────────────────────────────╮
# │  Top Banner + Theme Switcher               │
# ╰────────────────────────────────────────────╯
def show_top_banner():
    st.markdown("""
        <style>
            .guzo-banner {
                background: linear-gradient(90deg,#004AAD,#0078FF);
                color:white; padding:0.6rem 1rem;
                border-radius:0.5rem; display:flex;
                justify-content:space-between; align-items:center;
                margin-bottom:1rem;
            }
            .guzo-banner h2{margin:0;font-size:1.6rem;}
            .guzo-banner p{margin:0;font-size:0.85rem;color:#EAF3FF;}
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,6,1])
    with col1:
        logo_path = os.path.join(os.path.dirname(__file__),"assets","logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path,width=60)
        else:
            st.markdown("<div style='font-size:40px;'>🏨</div>",unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='guzo-banner'>
                <div>
                    <h2>Guzo Guest Assist</h2>
                    <p>Smart Hotel Automation & Guest Experience Dashboard</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        dark = st.toggle("🌗 Dark mode")
        st.session_state["theme"]="dark" if dark else "light"


# ╭────────────────────────────────────────────╮
# │  KPI Summary Section                       │
# ╰────────────────────────────────────────────╯
def show_summary(df):
    """Displays executive KPI cards."""
    col1,col2,col3 = st.columns(3)
    col1.metric("🏨 Total Hotels", len(df))
    try:
        if "RevPAR" in df.columns:
            avg_revpar = round(df["RevPAR"].astype(float).mean(),2)
        else:
            avg_revpar = "N/A"
    except Exception:
        avg_revpar = "N/A"
    col2.metric("💰 Average RevPAR", avg_revpar)
    col3.metric("📅 Last Sync", datetime.now().strftime("%H:%M:%S"))


# ╭────────────────────────────────────────────╮
# │  Home / Main Dashboard View                │
# ╰────────────────────────────────────────────╯
def show_home():
    show_top_banner()
    st.title("🏨 Guzo Guest Assist – Central Dashboard")
    st.caption("Unified control center for hotel performance and automation.")

    try:
        st.info("🔄 Initializing Google Sheets client ...")
        google_sheets.init_client()
        st.success("✅ Google Sheets client initialized successfully.")

        sheet_id = os.getenv("HOTEL_CONTACTS_SHEET_ID","")
        if not sheet_id:
            st.warning("⚠️ No Hotel Contacts Sheet ID found in .env file.")
        else:
            st.write(f"🔍 Using Hotel Contacts Sheet ID: `{sheet_id[:20]}...`")

        df = google_sheets.load_hotel_contacts()
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str)

        show_summary(df)
        st.success(f"✅ Loaded {len(df)} hotel contacts successfully.")
        st.dataframe(df, width="stretch")

    except Exception as e:
        st.error(f"❌ Error during initialization: {e}")

    st.markdown("---")
    st.write(f"📅 **Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("© 2025 Guzo Guest Assist | Confidential – Internal Use Only")


# ╭────────────────────────────────────────────╮
# │  Entrypoint & Routing                      │
# ╰────────────────────────────────────────────╯
def init_app():
    st.set_page_config(
        page_title="Guzo Guest Assist Dashboard",
        layout="wide",
        page_icon="🏨",
    )
    page = show_sidebar()
    if page=="🏠 Home (Launcher)": show_home()
    elif page=="📊 Central Dashboard":
        import central_dashboard; central_dashboard.show_dashboard()
    elif page=="🧾 Notification Logs":
        import notification_logs_dashboard; notification_logs_dashboard.show_notification_logs()


if __name__=="__main__":
    init_app()
