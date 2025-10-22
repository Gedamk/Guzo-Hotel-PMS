# -*- coding: utf-8 -*-
"""
google_sheets.py – Guzo Guest Assist Google Sheets Integration
---------------------------------------------------------------
Handles read/write operations for hotel data and notification logs.
"""

import os
import gspread
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def _get_service():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        raise FileNotFoundError(f"Google credentials not found: {creds}")
    return gspread.service_account(filename=creds)

def fetch_data(sheet_id: str) -> pd.DataFrame:
    sa = _get_service()
    sh = sa.open_by_key(sheet_id)
    ws = sh.sheet1
    df = pd.DataFrame(ws.get_all_records())
    return df

def append_row(sheet_id: str, row_values: list):
    sa = _get_service()
    sh = sa.open_by_key(sheet_id)
    ws = sh.sheet1
    ws.append_row(row_values)
