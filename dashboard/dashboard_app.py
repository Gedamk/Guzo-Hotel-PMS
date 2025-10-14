# -*- coding: utf-8 -*-
"""
Guzo Guest Assist Dashboard v13.6
Clean UTF-8 version with HTML auto-refresh
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import os, json, requests, pandas as pd, streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from streamlit_option_menu import option_menu
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---- ENVIRONMENT ----
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)

CITY = os.getenv("CITY", "Addis Ababa")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=ETB,EUR,GBP"
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials_prod.json")

HOTEL_NAME = os.getenv("HOTEL_NAME", "Guzo Guest Assist")
MANAGER_NAME = os.getenv("MANAGER_NAME", "Manager")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+251900000000")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "info@guzoassist.com")

# ---- AUTO REFRESH (HTML) ----
refresh_interval = int(os.getenv("REFRESH_INTERVAL", 60))
st.markdown(f"<meta http-equiv='refresh' content='{refresh_interval}'>", unsafe_allow_html=True)
st.caption(f"🔄 Dashboard auto-refreshes every {refresh_interval} seconds.")

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Guzo Guest Assist", page_icon="🏨", layout="wide")
st.title(f"🏨 {HOTEL_NAME} — Hospitality Control Center")
st.caption(f"Managed by {MANAGER_NAME} | 📞 {SUPPORT_PHONE} | ✉️ {SUPPORT_EMAIL}")
st.markdown("---")

st.success("✅ Dashboard loaded successfully — clean UTF-8 build.")
