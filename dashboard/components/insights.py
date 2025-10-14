# -*- coding: utf-8 -*-
"""
ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ¡ Guzo Guest Assist ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Live Insights Component
Reads and displays data directly from Google Sheets.
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
from datetime import datetime

# ----------------------------
# Google Sheets Connection
# ----------------------------
def get_sheets_client():
  creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
  scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
  creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
  return gspread.authorize(creds)

def read_sheet_data(sheet_name):
  try:
    client = get_sheets_client()
    sheet = client.open(sheet_name)
    worksheet = sheet.sheet1
    data = pd.DataFrame(worksheet.get_all_records())
    return data
  except Exception as e:
    st.error(f"ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ ÃÂÂÃÂÂÃÂÂÃÂÂ¯ÃÂÂÃÂÂÃÂÂÃÂÂ¸ÃÂÂÃÂÂÃÂÂÃÂÂ Unable to load {sheet_name}: {e}")
    return pd.DataFrame()

# ----------------------------
# Main Renderer
# ----------------------------
def render_insights():
  st.subheader("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Live Data Insights (Google Sheets)")

  guest_df = read_sheet_data("Guest Assist")
  contact_df = read_sheet_data("HotelContacts")
  notif_df = read_sheet_data("NotificationLogs")

  total_hotels = len(contact_df)
  total_guests = len(guest_df)
  total_msgs = len(notif_df)
  pending = notif_df[notif_df["Status"].str.lower() == "pending"].shape[0] if not notif_df.empty else 0

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ Active Hotels", total_hotels)
  c2.metric("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ Guests", total_guests)
  c3.metric("ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ Notifications", total_msgs)
  c4.metric("ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ³ Pending Replies", pending)

  st.divider()
  st.markdown("### ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ§ÃÂÂÃÂÂÃÂÂÃÂÂ¾ Recent Guest Bookings")
  if not guest_df.empty:
    st.dataframe(guest_df.tail(10), use_container_width=True, hide_index=True)
  else:
    st.info("No guest data found.")

  st.markdown("### ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ Recent Notifications")
  if not notif_df.empty:
    st.dataframe(notif_df.tail(10), use_container_width=True, hide_index=True)
  else:
    st.info("No notification data found.")

  st.caption(f"ÃÂÂÃÂÂÃÂÂÃÂÂ°ÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ Last updated: {datetime.now().strftime('%I:%M %p')}")
