# -*- coding: utf-8 -*-
"""
revenue_summary.py – Guzo Guest Assist Revenue Dashboard (v5.1)
---------------------------------------------------------------
Displays hotel revenue analytics and summary charts.
✅ Unified design with heritage header & footer
"""

import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv

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
    page_title="💰 Revenue Summary – Guzo Guest Assist",
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
        <h1 style="margin-bottom:0;">💰 Guzo Guest Assist – Revenue Summary</h1>
        <p style="margin-top:4px; font-size:15px; color:#FFB703;">
            ቆይታዎን እንረዳለን። — Your Stay, Our Assist.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================
# 📊 DEMO REVENUE DATA (Can be replaced with Google Sheets)
# ======================================================
st.subheader("📈 Monthly Revenue Overview")

data = {
    "Hotel": ["Sofi Hotel", "Sky Light", "Haile Resort", "Lewi Resort"],
    "Week 1": [68000, 85000, 91000, 52000],
    "Week 2": [72000, 89000, 94000, 55000],
    "Week 3": [74000, 92000, 98000, 57000],
    "Week 4": [75000, 95000, 100000, 59000],
}
df = pd.DataFrame(data)
df["Total Revenue (ETB)"] = df[["Week 1", "Week 2", "Week 3", "Week 4"]].sum(axis=1)

chart = px.bar(
    df,
    x="Hotel",
    y="Total Revenue (ETB)",
    color="Hotel",
    text="Total Revenue (ETB)",
    title="Hotel Monthly Revenue Comparison",
)
st.plotly_chart(chart, width="stretch")

# ======================================================
# 💡 INSIGHTS
# ======================================================
st.markdown("### 💡 Key Insights")
st.write("""
- **Sky Light Hotel** continues to lead revenue growth.
- **Sofi Hotel** maintains stable weekly performance.
- Total revenue has increased by **~8%** compared to the previous month.
""")

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
