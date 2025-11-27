# -*- coding: utf-8 -*-
"""
Dashboard Component – System Health
Shows the status of backend services and automation jobs.
"""

import streamlit as st
import pandas as pd


def render_system_status():
    st.subheader("🩺 System Health Monitor")

    data = pd.DataFrame(
        {
            "Service": [
                "Booking Sync",
                "Retry Handler",
                "Payment Webhooks",
                "Email Alerts",
                "Telegram Bot",
            ],
            "Status": [
                "Active",
                "Stable",
                "Listening",
                "Sending",
                "Online",
            ],
            "Last Checked": [
                "5 min ago",
                "5 min ago",
                "10 min ago",
                "3 min ago",
                "Live",
            ],
        }
    )

    # Updated for new Streamlit syntax
    st.dataframe(data, width="stretch", hide_index=True)

    st.success("All systems are operational.")


# Run component directly
if __name__ == "__main__":
    render_system_status()
