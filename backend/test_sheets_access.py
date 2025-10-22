# -*- coding: utf-8 -*-
"""
Google Sheets Connection Tester – Guzo Guest Assist (Auto-Fix v2)
-----------------------------------------------------------------
Automatically detects the correct Google credentials path.
"""

import os
import gspread
from dotenv import load_dotenv

# Load env file
load_dotenv()

# 🧩 Auto-detect credentials file
possible_paths = [
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    r"C:\Users\Gedan\Desktop\Guzo\guzo_booking_bot\creds\guzo_service_account.json",
    r"C:\Users\Gedan\Desktop\Guzo\creds\guzo_service_account.json"
]

CREDS = None
for path in possible_paths:
    if path and os.path.exists(path):
        CREDS = path
        break

if not CREDS:
    print("❌ No valid credentials file found. Check paths manually.")
    exit()

print(f"🧩 Using credentials: {CREDS}")

try:
    sa = gspread.service_account(filename=CREDS)
except Exception as e:
    print(f"❌ Could not load service account: {e}")
    exit()

# 🔧 Replace with your actual Sheet IDs
hotels = [
    ("Sofi Hotel", "1YltAe8EAo5LGDt5r5PnrbU9RmE8TS8no8ryd5-3vxb8"),
    ("Sky Light Hotel", "1VAnieaVMqh_y-17hifwYIUFpxUj5_oD2QS0i-kyD8XQ"),
    ("Haile Resort", "1ny6-MShhSGb4_lXf7PfB25pMTL9chfSgBqobcPngcGQ"),
    ("Lewi Resort & Spa", "1lKsz6XHzdSfegltfeFW7CyK5dYwTRLLqUvPqXMQlwy4"),
    ("Hilton Addis Hotel", "18VU53Q1vXGYo4FKXbc6QJF1e2rUjhMdBDsxzIprS5Ok"),
]

for name, sid in hotels:
    try:
        sh = sa.open_by_key(sid)
        print(f"✅ {name} connected → Sheet title: {sh.title}")
    except Exception as e:
        print(f"❌ {name} failed → {e}")

