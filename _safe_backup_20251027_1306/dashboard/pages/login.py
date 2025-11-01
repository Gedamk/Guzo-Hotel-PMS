# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Secure Login (v1.1)
---------------------------------------
Authenticates Central Admin and Hotel Managers,
links manager emails to their hotel via Google Sheets,
and routes them to the correct dashboard.
"""

import streamlit as st
import os
from dotenv import load_dotenv
from guzo_booking_bot.modules import google_sheets

# ===========================================
# ENVIRONMENT SETUP
# ===========================================
load_dotenv()

st.set_page_config(
    page_title="Guzo Login Portal",
    page_icon="🔐",
    layout="centered",
)

st.title("🔐 Guzo Guest Assist Login")
st.caption("Secure Access for Central Admin & Hotel Managers")

# ===========================================
# LOGIN FORM
# ===========================================
username = st.text_input("Email / Username")
password = st.text_input("Password", type="password")
login_button = st.button("Login")

# ===========================================
# CREDENTIALS (from .env)
# ===========================================
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin@guzo.com")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123")
MANAGER_PASS = os.getenv("MANAGER_DEFAULT_PASSWORD", "guestassist")

# ===========================================
# MANAGER MAPPING (Google Sheets lookup)
# ===========================================
try:
    google_sheets.init_client()
    df_hotels = google_sheets.load_hotel_contacts()
    manager_map = {
        row["Main Contact Email"]: row["Hotel Name"]
        for _, row in df_hotels.iterrows()
        if row.get("Main Contact Email") and row.get("Hotel Name")
    }
except Exception as e:
    manager_map = {}
    st.sidebar.warning("⚠️ Could not load hotel manager list from Google Sheets.")

# ===========================================
# LOGIN LOGIC
# ===========================================
if login_button:
    # ---- Central Admin ----
    if username == ADMIN_USER and password == ADMIN_PASS:
        st.session_state["role"] = "admin"
        st.session_state["user"] = ADMIN_USER
        st.session_state["hotel_name"] = "Central System"
        st.success("✅ Logged in as Central Admin")
        st.switch_page("dashboard/central_dashboard.py")

    # ---- Hotel Manager ----
    elif username in manager_map and password == MANAGER_PASS:
        st.session_state["role"] = "manager"
        st.session_state["user"] = username
        st.session_state["hotel_name"] = manager_map[username]
        st.success(f"✅ Logged in as Manager of {manager_map[username]}")
        st.switch_page("dashboard/app.py")

    # ---- Invalid ----
    else:
        st.error("❌ Invalid credentials or unauthorized user.")

# ===========================================
# FOOTER
# ===========================================
st.markdown("---")
st.caption("© 2025 Guzo Guest Assist | Developed by Gedam Kacha")
