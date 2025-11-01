# -*- coding: utf-8 -*-
"""
hotel_overview.py – Guzo Guest Assist Hotel Overview (v5.1)
------------------------------------------------------------
Displays partner hotel details, contacts, and performance.
✅ Unified with Manager Center header/footer style
"""

import os
import sys
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from guzo_backend.modules import google_sheets

# ======================================================
# 🌍 ENVIRONMENT SETUP
# ======================================================
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path=env_path, override=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ======================================================
# 🧩 STREAMLIT CONFIG
# ======================================================
st.set_page_config(
    page_title="🏢 Hotel Overview – Guzo Guest Assist",
    layout="wide",
)

# ======================================================
# 🌟 HEADER (Same as Manager Center)
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
        <h1 style="margin-bottom:0;">🏢 Guzo Guest Assist – Hotel Overview</h1>
        <p style="margin-top:4px; font-size:15px; color:#FFB703;">
            ቆይታዎን እንረዳለን። — Your Stay, Our Assist.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================
# 🧾 HOTEL CONTACTS (Google Sheets or Demo Data)
# ======================================================
st.subheader("🏨 Partner Hotels and Contact Information")

try:
    contacts = google_sheets.get_hotel_contacts()
    if contacts:
        df = pd.DataFrame(contacts)
        st.success(f"✅ Loaded {len(df)} hotel contacts from Google Sheets.")
    else:
        st.warning("⚠️ No hotel data found. Showing demo dataset.")
        df = pd.DataFrame([
            {"Hotel Name": "Sofi Hotel", "Email": "info@sofi.com", "Phone": "+251911223344"},
            {"Hotel Name": "Sky Light", "Email": "contact@skylight.com", "Phone": "+251922556677"},
            {"Hotel Name": "Haile Resort", "Email": "hello@haile.com", "Phone": "+251933445566"},
            {"Hotel Name": "Lewi Resort", "Email": "book@lewi.com", "Phone": "+251944556677"},
        ])
except Exception as e:
    st.error(f"❌ Error loading hotel data: {e}")
    df = pd.DataFrame()

if not df.empty:
    st.dataframe(df, width="stretch", height=350)

# ======================================================
# 📊 PERFORMANCE SNAPSHOT
# ======================================================
st.markdown("### 📊 Occupancy & Performance Overview")

performance = {
    "Hotel": ["Sofi Hotel", "Sky Light", "Haile Resort", "Lewi Resort"],
    "Occupancy (%)": [82, 91, 77, 84],
    "Available Rooms": [60, 75, 50, 65],
}
perf_df = pd.DataFrame(performance)
st.bar_chart(perf_df.set_index("Hotel"))

# ======================================================
# 🌍 FOOTER (Unified Heritage Design)
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
