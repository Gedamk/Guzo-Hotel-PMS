# -*- coding: utf-8 -*-
"""
channel_selector.py
-------------------------------------------------------
Selects the best available communication channel for each hotel.
Priority order: Telegram → WhatsApp → Email → SMS → Website
"""

import pandas as pd

def select_best_channel(hotel_row):
    """
    Decide which communication channel to use for a hotel.

    Args:
        hotel_row (pd.Series): One row from the hotel directory DataFrame

    Returns:
        dict: selected channel info {type, value}
    """

    # Extract fields safely
    telegram = str(hotel_row.get("Telegram", "")).strip()
    whatsapp = str(hotel_row.get("WhatsApp", "")).strip()
    email = str(hotel_row.get("Email", "")).strip()
    sms = str(hotel_row.get("SMS Number", "")).strip()
    website = str(hotel_row.get("Website", "")).strip()

    # Priority order
    if telegram and telegram.lower() not in ["nan", "none", ""]:
        return {"type": "telegram", "value": telegram}

    elif whatsapp and whatsapp.lower() not in ["nan", "none", ""]:
        return {"type": "whatsapp", "value": whatsapp}

    elif email and email.lower() not in ["nan", "none", ""]:
        return {"type": "email", "value": email}

    elif sms and sms.lower() not in ["nan", "none", ""]:
        return {"type": "sms", "value": sms}

    elif website and website.lower() not in ["nan", "none", ""]:
        return {"type": "website", "value": website}

    else:
        return {"type": "none", "value": None}


# 🧪 Optional test function
if __name__ == "__main__":
    from guzo_backend.utils.hotel_directory import fetch_hotel_data
    hotels_df = fetch_hotel_data()

    for _, row in hotels_df.iterrows():
        choice = select_best_channel(row)
        print(f"🏨 {row['Hotel Name']}: using {choice['type']} → {choice['value']}")
