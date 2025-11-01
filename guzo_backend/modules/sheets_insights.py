# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂ³ÃÂÃÂÃÂÃÂ Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Google Sheets Insights Engine (v2.0)
-----------------------------------------------------------
Pulls and analyzes booking and guest trend data directly from
Google Sheets defined in .env:
  - GUEST_ASSIST_SHEET
  - HOTEL_CONTACT_SHEET

Outputs summarized statistics and charts for the dashboard.
"""

import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

# ======================================================
# CONFIG
# ======================================================
GUEST_SHEET_URL = os.getenv("GUEST_ASSIST_SHEET")
CONTACT_SHEET_URL = os.getenv("HOTEL_CONTACT_SHEET")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# ======================================================
# GOOGLE SHEETS CONNECTION
# ======================================================
def connect_google_sheets():
    """Authenticate and return gspread client."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        return client, None
    except Exception as e:
        return None, str(e)


def read_sheet(url):
    """Return a pandas DataFrame from a Google Sheet."""
    client, err = connect_google_sheets()
    if not client:
        return pd.DataFrame(), err
    try:
        sheet = client.open_by_url(url).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)


# ======================================================
# ANALYTICS FUNCTIONS
# ======================================================
def summarize_guests():
    """Summarize total guests and source channels."""
    df, err = read_sheet(GUEST_SHEET_URL)
    if df.empty:
        return {"status": "no_data", "error": err or "No guest data found."}

    stats = {
        "total_guests": len(df),
        "unique_properties": df["Property"].nunique() if "Property" in df else 0,
        "top_channel": df["Channel"].value_counts().idxmax() if "Channel" in df else "N/A",
        "top_country": df["Country"].value_counts().idxmax() if "Country" in df else "N/A",
    }
    return stats


def daily_bookings():
    """Return daily booking counts as a DataFrame for plotting."""
    df, _ = read_sheet(GUEST_SHEET_URL)
    if df.empty or "Booking Date" not in df.columns:
        return pd.DataFrame()

    df["Booking Date"] = pd.to_datetime(df["Booking Date"], errors="coerce")
    df = df.dropna(subset=["Booking Date"])
    trend = df.groupby(df["Booking Date"].dt.date).size().reset_index(name="Bookings")
    return trend


def top_properties(n=5):
    """Return top performing properties by guest count."""
    df, _ = read_sheet(GUEST_SHEET_URL)
    if df.empty or "Property" not in df.columns:
        return pd.DataFrame()
    prop = df["Property"].value_counts().reset_index()
    prop.columns = ["Property", "Guests"]
    return prop.head(n)
