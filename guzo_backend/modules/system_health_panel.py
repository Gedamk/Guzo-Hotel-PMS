# -*- coding: utf-8 -*-
"""
system_health_panel.py – Guzo Guest Assist System Health & Property Monitor
---------------------------------------------------------------------------
Displays live status for Google Sheets, SendGrid, Telegram, WhatsApp, Stripe,
and Telebirr integrations — and lists active hotel properties.
"""

import os
import requests
import streamlit as st
from dotenv import load_dotenv
from guzo_backend.modules import google_sheets, telegram_notifier, whatsapp_sender

# Load environment
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEBIRR_API_URL = os.getenv("TELEBIRR_API_URL", "https://api.telebirr.com/payments")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")

def check_google_sheets():
    try:
        status = google_sheets.get_test_sheet_status()
        return True, status or "✅ Connected"
    except Exception as e:
        return False, f"❌ {e}"

def check_sendgrid():
    return (True, "✅ Key Loaded") if SENDGRID_API_KEY and len(SENDGRID_API_KEY) > 20 else (False, "❌ Missing Key")

def check_telegram():
    try:
        resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=8)
        if resp.status_code == 200:
            bot_name = resp.json()["result"]["username"]
            return True, f"✅ @{bot_name}"
        return False, f"❌ {resp.text}"
    except Exception as e:
        return False, f"❌ {e}"

def check_whatsapp():
    try:
        whatsapp_sender.send_whatsapp_message("+12025550123", "🟢 WhatsApp test (simulation)")
        return True, "✅ Simulation Active"
    except Exception as e:
        return False, f"❌ {e}"

def check_stripe():
    return (True, "✅ Key Loaded") if STRIPE_KEY and len(STRIPE_KEY) > 10 else (False, "❌ Missing Stripe Key")

def check_telebirr():
    try:
        resp = requests.get(TELEBIRR_API_URL, timeout=5)
        if resp.status_code in (200, 403, 404):
            return True, "✅ API Reachable"
        return False, f"❌ Status {resp.status_code}"
    except Exception as e:
        return False, f"❌ {e}"

def load_hotel_properties():
    """
    Reads hotel property list from Google Sheets (Hotel_Contacts_Master).
    """
    try:
        df = google_sheets.read_hotels_master()
        return df
    except Exception as e:
        st.warning(f"⚠️ Could not load hotel list from Google Sheets: {e}")
        return None

def show_health_panel():
    st.markdown("## 🩺 System Health Panel")
    st.caption("Live status of all backend integrations for Guzo Guest Assist.")
    st.divider()

    checks = {
        "Google Sheets": check_google_sheets,
        "SendGrid Email": check_sendgrid,
        "Telegram Bot": check_telegram,
        "WhatsApp Sender": check_whatsapp,
        "Stripe Payments": check_stripe,
        "Telebirr Payments": check_telebirr,
    }

    cols = st.columns(3)
    for i, (name, fn) in enumerate(checks.items()):
        ok, msg = fn()
        icon = "🟢" if ok else "🔴"
        with cols[i % 3]:
            st.metric(label=f"{icon} {name}", value=msg)

    st.divider()
    st.markdown("### 🏨 Active Hotel Properties")

    df = load_hotel_properties()
    if df is not None and not df.empty:
        display_cols = [col for col in df.columns if col.lower() in ["hotel name", "property code", "location", "integration status"]]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No hotel data found in Google Sheets or sheet is empty.")
