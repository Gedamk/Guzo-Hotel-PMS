# -*- coding: utf-8 -*-
"""
sheet_logger.py
Logs all messages from any source into a local CSV file (simulating Google Sheets).
"""

import csv
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "messages_log.csv")

def log_message(source: str, sender: str, message: str):
    """Append message info into a CSV log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), source, sender, message])
    print(f"[LOG] {source} message logged from {sender}.")
