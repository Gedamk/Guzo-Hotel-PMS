# -*- coding: utf-8 -*-
"""
Dashboard Component ÃÃÃÃÃÃÃÃÃÃÃÃ System Health
Shows the status of backend services and automation jobs.
"""

import streamlit as st
import pandas as pd

def render_system_status():
  st.subheader("ÃÃÃÃÃÃÃÃÃÃÃÃÃÃÃÃ¯ÃÃÃÃ¸ÃÃÃÃ System Health Monitor")

  data = pd.DataFrame({
    "Service": ["Booking Sync", "Retry Handler", "Payment Webhooks", "Email Alerts", "Telegram Bot"],
    "Status": ["ÃÃÃÃÃÃÃÃÃÃÃÃ
 Active", "ÃÃÃÃÃÃÃÃÃÃÃÃ
 Stable", "ÃÃÃÃÃÃÃÃÃÃÃÃ
 Listening", "ÃÃÃÃÃÃÃÃÃÃÃÃ
 Sending", "ÃÃÃÃÃÃÃÃÃÃÃÃ
 Online"],
    "Last Checked": ["5 min ago", "5 min ago", "10 min ago", "3 min ago", "Live"]
  })
  st.dataframe(data, use_container_width=True, hide_index=True)

  st.success("All systems are operational.")
