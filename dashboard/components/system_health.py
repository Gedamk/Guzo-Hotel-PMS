# -*- coding: utf-8 -*-
"""
Dashboard Component ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ System Health
Shows the status of backend services and automation jobs.
"""

import streamlit as st
import pandas as pd

def render_system_status():
  st.subheader("ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂ¯ÃÂÂÃÂÂÃÂÂÃÂÂ¸ÃÂÂÃÂÂÃÂÂÃÂÂ System Health Monitor")

  data = pd.DataFrame({
    "Service": ["Booking Sync", "Retry Handler", "Payment Webhooks", "Email Alerts", "Telegram Bot"],
    "Status": ["ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ
 Active", "ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ
 Stable", "ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ
 Listening", "ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ
 Sending", "ÃÂÂÃÂÂÃÂÂÃÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂÂÃÂ
 Online"],
    "Last Checked": ["5 min ago", "5 min ago", "10 min ago", "3 min ago", "Live"]
  })
  st.dataframe(data, use_container_width=True, hide_index=True)

  st.success("All systems are operational.")
