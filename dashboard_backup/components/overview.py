# -*- coding: utf-8 -*-
"""
Dashboard Component ÃÃÃÃÃÃÃÃÃÃÃÃ Overview
Displays general hotel performance metrics and booking highlights.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

def render_overview():
  st.subheader("ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Property Overview")

  # Key KPIs
  metrics = {
    "Today's Bookings": 14,
    "Guests Checked In": 10,
    "Pending Replies": 4,
    "Occupancy Rate": "86%",
    "Revenue (ETB)": "ÃÃÃÃÃÃÃÃÃÃÃÃµ 78,900"
  }

  cols = st.columns(len(metrics))
  for i, (label, value) in enumerate(metrics.items()):
    cols[i].metric(label, value)

  st.markdown("### ÃÃÃÃ°ÃÃÃÃÃÃÃÃÃÃÃÃ Booking Snapshot")

  demo = pd.DataFrame({
    "Guest": ["Sara", "Luel", "Michael", "Hana", "Robel"],
    "Hotel": ["Zoma", "Hyatt", "Hilton", "Marriott", "Skylight"],
    "Status": ["Confirmed", "Pending", "Processed", "Checked-in", "Cancelled"],
    "Check-in": ["Oct 11", "Oct 12", "Oct 10", "Oct 11", "Oct 9"],
    "Nights": [3, 2, 1, 4, 2],
  })
  st.dataframe(demo, use_container_width=True, hide_index=True)

  st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
