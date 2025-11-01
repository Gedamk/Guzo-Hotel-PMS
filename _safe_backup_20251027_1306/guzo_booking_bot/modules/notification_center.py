# -*- coding: utf-8 -*-
"""
notification_center.py – Unified Email + Telegram Notifications for Guzo Guest Assist
------------------------------------------------------------------------------------
• Sends bilingual weekly summary emails via SendGrid
• Sends Telegram alert to managers group
"""

import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import requests
from guzo_booking_bot.modules.env_loader import init_env

# Load environment
init_env()

def send_weekly_summary(report_path, context):
    """Send bilingual weekly summary email + Telegram alert."""
    api_key = os.getenv("SENDGRID_API_KEY")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("MANAGER_CHAT_ID")  # from .env
    from_email = os.getenv("FROM_EMAIL", "reports@guzoassist.com")
    to_email = os.getenv("TO_EMAIL", "owner@guzoassist.com")

    if not api_key:
        print("❌ Missing SENDGRID_API_KEY in environment.")
        return

    print("📨 Preparing bilingual email summary...")

    html_content = f"""
    <h2>Guzo Guest Assist – Weekly Summary</h2>
    <p><b>Hotel:</b> {context['hotel_name']}</p>
    <p><b>Occupancy:</b> {context['occupancy']}%</p>
    <p><b>ADR:</b> ETB {context['adr']}</p>
    <p><b>RevPAR:</b> ETB {context['revpar']}</p>
    <h3>Top Recommendations</h3>
    <ul>
      <li>{context['recommendation_1']}</li>
      <li>{context['recommendation_2']}</li>
      <li>{context['recommendation_3']}</li>
    </ul>
    <hr>
    <h4>በአማርኛ ሪፖርት</h4>
    <ul>
      <li>{context['recommendation_1_am']}</li>
      <li>{context['recommendation_2_am']}</li>
      <li>{context['recommendation_3_am']}</li>
    </ul>
    """

    with open(report_path, "rb") as f:
        encoded_file = base64.b64encode(f.read()).decode()

    attachment = Attachment(
        FileContent(encoded_file),
        FileName(os.path.basename(report_path)),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f"Weekly Report – {context['hotel_name']}",
        html_content=html_content
    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✅ Email sent successfully! Status Code: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")

    # Telegram alert
    if telegram_token and telegram_chat_id:
        msg = f"📊 Weekly report sent for *{context['hotel_name']}* ✅\nOccupancy: {context['occupancy']}% | ADR: {context['adr']} | RevPAR: {context['revpar']}"
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("📩 Telegram notification delivered successfully.")
            else:
                print("⚠️ Telegram notification failed:", res.text)
        except Exception as e:
            print("⚠️ Telegram error:", e)
