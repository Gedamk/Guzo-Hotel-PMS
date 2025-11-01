# -*- coding: utf-8 -*-
"""
Guzo Guest Assist – Manager Center (Heritage & Hospitality Edition)
-------------------------------------------------------------------
Unified dashboard reflecting Guzo Guest Assist's cultural identity,
hospitality professionalism, and mission:
“ቆይታዎን እንረዳለን። — Your Stay, Our Assist.”
"""

import os
import base64
import subprocess
from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ✅ Register font that supports Amharic text
pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

# ======================================================
# 🌍 Page Config
# ======================================================
st.set_page_config(
    page_title="Guzo Guest Assist – Manager Center",
    page_icon="🏨",
    layout="wide",
)

# ======================================================
# 🌟 Header
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
        <h1 style="margin-bottom:0;">🏨 Guzo Guest Assist – Manager Center</h1>
        <p style="margin-top:4px; font-size:15px; color:#FFB703;">
            ቆይታዎን እንረዳለን። — Your Stay, Our Assist.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================
# 🧭 Sidebar
# ======================================================
logo_path = "assets/guzo_logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=160)
else:
    st.sidebar.markdown("### 🏨 Guzo Guest Assist")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Guzo Guest Assist**  
    Empowering Ethiopian Hospitality with Global Technology.  
    ቆይታዎን እንረዳለን።
    """
)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "📋 Manager Dashboard",
    [
        "🏠 Dashboard Overview",
        "📢 Notifications & Alerts",
        "📊 Performance Reports",
        "💬 Guest Feedback Logs",
        "🛠️ System Health & Logs",
    ],
)
st.sidebar.markdown("---")
st.sidebar.success(f"📅 {datetime.now().strftime('%A, %B %d, %Y')}")

# ======================================================
# 🧭 Manager Action Bar
# ======================================================
st.markdown(
    "<h3 style='color:#004B8D; border-left:5px solid #FFB703; padding-left:10px;'>🧭 Manager Actions</h3>",
    unsafe_allow_html=True,
)
colA, colB, colC, colD = st.columns([1, 1, 1, 1])
load_dotenv(dotenv_path=".env", override=True)

# ======================================================
# 📘 Helper – Generate bilingual PDF
# ======================================================
def generate_bilingual_pdf(include_logs=True):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName = "HYSMyeongJo-Medium"

    content = []

    if os.path.exists(logo_path):
        content.append(Image(logo_path, width=120, height=60))
        content.append(Spacer(1, 10))

    content.append(
        Paragraph("<b style='color:#004B8D;'>Guzo Guest Assist – Booking & System Report</b>", styles["Title"])
    )
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    content.append(Spacer(1, 10))

    booking_data = [
        ["👤 Guest Name", "Selam Abebe / ሰላም አበበ"],
        ["🏨 Hotel", "Sofi Hotel / ሶፊ ሆቴል"],
        ["📅 Check-In", "2025-10-25"],
        ["🛏️ Nights", "3"],
        ["🚪 Room Type", "Executive Suite"],
        ["💰 Rate (ETB)", "2800"],
        ["📞 Contact", "+251987006170"],
        ["📊 Status", "Confirmed / ተረጋጋ"],
    ]
    table = Table(booking_data, colWidths=[140, 300])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, colors.gray),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAF9F6")),
                ("FONTNAME", (0, 0), (-1, -1), "HYSMyeongJo-Medium"),
            ]
        )
    )
    content.append(table)
    content.append(Spacer(1, 20))

    if include_logs:
        content.append(Paragraph("<b style='color:#004B8D;'>📜 System Activity Log / የስርዓት መዝገብ</b>", styles["Heading3"]))
        content.append(Spacer(1, 6))

        log_file = os.path.join("logs", "system_events.log")
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-20:]
            log_data = [["Time / ሰዓት", "Module / ክፍል", "Message / መልእክት"]]
            for line in lines:
                parts = line.strip().split(" | ")
                if len(parts) == 3:
                    t, m, msg = parts
                    log_data.append([t.replace("[", "").replace("]", ""), m, msg])
        else:
            log_data = [["-", "-", "No log entries found / መዝገብ አልተገኘም"]]

        log_table = Table(log_data, colWidths=[120, 100, 220])
        log_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFB703")),
                    ("FONTNAME", (0, 0), (-1, -1), "HYSMyeongJo-Medium"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        content.append(log_table)
        content.append(Spacer(1, 20))

    content.append(Paragraph("ቆይታዎን እንረዳለን። — Your Stay, Our Assist.", styles["Italic"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph("አመሰግናለሁ። እንደገና እንገናኛለን።", styles["Normal"]))
    content.append(Spacer(1, 6))
    content.append(Paragraph("Thank you for choosing Guzo Guest Assist.", styles["Normal"]))
    content.append(Spacer(1, 15))
    content.append(Paragraph("<b>Signature:</b> ____________________________", styles["Normal"]))

    doc.build(content)
    data = buffer.getvalue()
    buffer.close()
    return data

# ======================================================
# 📤 Send Weekly Report
# ======================================================
with colA:
    if st.button("📤 Send Weekly Report", width='stretch'):
        st.info("Preparing bilingual report email with attachment...")
        try:
            api = os.getenv("SENDGRID_API_KEY")
            sender = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
            recipient = os.getenv("TO_EMAIL", "owner@guzoassist.com")
            pdf_bytes = generate_bilingual_pdf()
            encoded = base64.b64encode(pdf_bytes).decode()

            attachment = Attachment()
            attachment.file_content = encoded
            attachment.file_type = "application/pdf"
            attachment.file_name = "Guzo_Report_with_Logs.pdf"
            attachment.disposition = "attachment"

            msg = Mail(
                from_email=sender,
                to_emails=recipient,
                subject="[Guzo] Weekly Manager Report",
                html_content=f"""
                <h3>Guzo Guest Assist – Weekly Summary</h3>
                <p>Your bilingual report for {datetime.now().strftime("%B %d, %Y")} is attached below.</p>
                <hr><em>ቆይታዎን እንረዳለን። — Your Stay, Our Assist.</em>
                """,
            )
            msg.attachment = attachment
            sg = SendGridAPIClient(api)
            sg.send(msg)
            st.success(f"✅ Report sent to {recipient}")
        except Exception as e:
            st.error(f"❌ Failed: {e}")

# ======================================================
# 📊 Generate Reports
# ======================================================
with colB:
    if st.button("📊 Generate Latest Reports", width='stretch'):
        st.info("Running backend weekly_summary.py ...")
        try:
            result = subprocess.run(
                ["python", "backend/weekly_summary.py"], capture_output=True, text=True, check=True
            )
            st.success("✅ Weekly summary completed.")
            st.text_area("System Output", result.stdout, height=150)
        except subprocess.CalledProcessError as e:
            st.error("❌ Error running weekly_summary.py:")
            st.text(e.stderr)

# ======================================================
# 📥 Download PDF
# ======================================================
with colC:
    if st.button("📥 Download Bilingual Report (PDF)", width='stretch'):
        pdf = generate_bilingual_pdf()
        st.download_button(
            label="⬇️ Click to Download PDF",
            data=pdf,
            file_name="Guzo_Report_with_Logs.pdf",
            mime="application/pdf",
            width='stretch'
        )
        st.success("✅ Bilingual report ready!")

# ======================================================
# 🔄 Refresh
# ======================================================
with colD:
    if st.button("🔄 Refresh Dashboard", width='stretch'):
        st.cache_data.clear()
        st.rerun()

st.markdown("<hr style='border:1px solid #FFB703;'>", unsafe_allow_html=True)

# ======================================================
# MAIN SECTIONS
# ======================================================
if menu == "🏠 Dashboard Overview":
    st.subheader("🏨 Hotel Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Hotels", 5, "+1 new this week")
    col2.metric("Total Rooms Managed", 242)
    col3.metric("Occupancy (Current Week)", "78%", "▲ 3%")

    st.markdown("---")
    hotels = ["All Hotels", "Sofi Hotel", "Sky Light Hotel", "Haile Resort", "Lewi Resort", "Golden Tulip"]
    sel = st.selectbox("🏨 Select Hotel", hotels, index=0)
    bookings = [
        {"Guest": "Selam Abebe", "Hotel": "Sofi Hotel", "Status": "Confirmed", "Check-in": "2025-10-25", "Nights": 3},
        {"Guest": "Abel Yonas", "Hotel": "Sky Light", "Status": "Pending", "Check-in": "2025-10-24", "Nights": 1},
        {"Guest": "Hanna Bekele", "Hotel": "Haile Resort", "Status": "Confirmed", "Check-in": "2025-10-23", "Nights": 2},
    ]
    df = pd.DataFrame([b for b in bookings if sel in ("All Hotels", b["Hotel"])])
    st.dataframe(df, width='stretch')

elif menu == "📢 Notifications & Alerts":
    st.subheader("📢 System Notifications & Alerts")
    st.warning("New booking received for Sofi Hotel")
    st.warning("Sky Light Hotel occupancy reached 80%")
    st.info("Twilio SMS delay resolved successfully.")

elif menu == "📊 Performance Reports":
    st.subheader("📊 Weekly Performance Overview")
    labels = ['Sofi Hotel', 'Sky Light', 'Haile Resort', 'Lewi Resort', 'Golden Tulip']
    values = [12000, 8500, 10000, 7800, 9600]
    fig, ax = plt.subplots()
    ax.bar(labels, values, color="#004B8D")
    ax.set_title("Weekly Revenue (ETB)", color="#004B8D")
    st.pyplot(fig)

elif menu == "💬 Guest Feedback Logs":
    st.subheader("💬 Guest Feedback")
    feedback = [
        {"Guest": "Selam Abebe", "Feedback": "Excellent room service."},
        {"Guest": "Abel Yonas", "Feedback": "Smooth check-in, friendly staff."},
        {"Guest": "Hanna Bekele", "Feedback": "Breakfast could be improved."},
    ]
    st.dataframe(pd.DataFrame(feedback), width='stretch')

elif menu == "🛠️ System Health & Logs":
    st.subheader("🛠️ System Health Monitor")
    health = {"Google Sheets": "✅ Connected", "SendGrid": "✅ OK", "Telegram": "✅ OK", "Twilio": "⚠️ Intermittent"}
    st.table(pd.DataFrame(list(health.items()), columns=["Service", "Status"]))

    st.markdown("---")
    st.subheader("📜 System Event Log (auto-refresh every 60s)")
    st.markdown("<meta http-equiv='refresh' content='60'>", unsafe_allow_html=True)
    log_file = "logs/system_events.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()[-30:]
        if lines:
            logs = []
            for line in lines:
                parts = line.strip().split(" | ")
                if len(parts) == 3:
                    ts, module, msg = parts
                    logs.append({"⏰ Time": ts.replace("[", "").replace("]", ""), "📦 Module": module, "🧾 Message": msg})
            st.dataframe(pd.DataFrame(logs), width='stretch')
        else:
            st.info("No log entries yet.")
    else:
        st.warning("No log file found at logs/system_events.log.")

# ======================================================
# 🌍 Footer
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
