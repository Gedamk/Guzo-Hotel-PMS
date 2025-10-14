# -*- coding: utf-8 -*-
"""
ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ¡ Guzo Guest Assist ÃÃÃÃÃÃÃÃÃÃÃÃ Live Insights Component
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
    st.error(f"ÃÃÃÃÃÃÃÃÃÃÃÃ ÃÃÃÃ¯ÃÃÃÃ¸ÃÃÃÃ Unable to load {sheet_name}: {e}")
    return pd.DataFrame()

# ----------------------------
# Main Renderer
# ----------------------------
def render_insights():
  st.subheader("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Live Data Insights (Google Sheets)")

  guest_df = read_sheet_data("Guest Assist")
  contact_df = read_sheet_data("HotelContacts")
  notif_df = read_sheet_data("NotificationLogs")

  total_hotels = len(contact_df)
  total_guests = len(guest_df)
  total_msgs = len(notif_df)
  pending = notif_df[notif_df["Status"].str.lower() == "pending"].shape[0] if not notif_df.empty else 0

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Active Hotels", total_hotels)
  c2.metric("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Guests", total_guests)
  c3.metric("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Notifications", total_msgs)
  c4.metric("ÃÃÃÃÃÃÃÃÃÃÃÃ³ Pending Replies", pending)

  st.divider()
  st.markdown("### ÃÃÃÃ°ÃÃÃÃÃÃÃÃ§ÃÃÃÃ¾ Recent Guest Bookings")
  if not guest_df.empty:
    st.dataframe(guest_df.tail(10), use_container_width=True, hide_index=True)
  else:
    st.info("No guest data found.")

  st.markdown("### ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Recent Notifications")
  if not notif_df.empty:
    st.dataframe(notif_df.tail(10), use_container_width=True, hide_index=True)
  else:
    st.info("No notification data found.")

  st.caption(f"ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Last updated: {datetime.now().strftime('%I:%M %p')}")
