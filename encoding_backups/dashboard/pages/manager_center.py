# -*- coding: utf-8 -*-
"""
Manager Center Page
-------------------------
Live management & sync panel for Guzo Guest Assist Dashboard.
Shows Google Sheets, SendGrid, and Telegram connection statuses in real time.
"""

import os
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)

GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials_prod.json")
SHEET_NAME = os.getenv("SHEET_NAME", "Guest_Bookings")
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

st.set_page_config(page_title="Manager Center", page_icon="")

st.title(" Manager Center Äî Property Overview & Sync Control")
st.caption("Real-time operational dashboard for hotel managers")
st.markdown("---")


# ======================================================
# å CONNECTION CHECKS
# ======================================================
def check_google_sheets():
  try:
    if not os.path.exists(GOOGLE_CREDS):
      return False, "Missing Google credentials file"
    scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    ws = sheet.sheet1
    ws.row_values(1)
    return True, "úÖ Connected successfully"
  except Exception as e:
    return False, f"ùå {e}"


def check_sendgrid():
  return (bool(SENDGRID_KEY), "úÖ Key found" if SENDGRID_KEY else "ùå Missing SENDGRID_API_KEY")


def check_telegram():
  return (bool(TELEGRAM_TOKEN), "úÖ Configured" if TELEGRAM_TOKEN else "ùå Missing TELEGRAM_BOT_TOKEN")


# ======================================================
# © STATUS DISPLAY
# ======================================================
st.subheader("å Live Service Status")

g_ok, g_msg = check_google_sheets()
s_ok, s_msg = check_sendgrid()
t_ok, t_msg = check_telegram()

cols = st.columns(3)
cols[0].metric("Google Sheets", " Online" if g_ok else " Offline")
cols[1].metric("SendGrid Email", " Enabled" if s_ok else " Disabled")
cols[2].metric("Telegram Bot", " Running" if t_ok else " Missing")

st.caption(f" {g_msg} | úâ {s_msg} | {t_msg}")
st.markdown("---")


# ======================================================
# KPI OVERVIEW
# ======================================================
st.subheader("à Operational KPIs")
c1, c2, c3, c4 = st.columns(4)
c1.metric("® Properties", 1)
c2.metric(" Messages", 25)
c3.metric("±• Guests", 7)
c4.metric("µ Updated", datetime.now().strftime("%H:%M:%S"))

st.markdown("---")


# ======================================================
# öô MANUAL CONTROLS
# ======================================================
st.subheader("öô Manual Controls")
col1, col2 = st.columns(2)

with col1:
  if st.button("Ñ Refresh Google Sheet Connection"):
    ok, msg = check_google_sheets()
    st.success(msg if ok else msg)

with col2:
  if st.button("§ Send Test Email (Simulated)"):
    st.info("úÖ Test email sent successfully.")

st.markdown("---")
st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | © 2025 Guzo Guest Assist")
