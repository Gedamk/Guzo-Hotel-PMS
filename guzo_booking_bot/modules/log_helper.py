# -*- coding: utf-8 -*-
"""
log_helper.py – Smart logging utility for Guzo Guest Assist
------------------------------------------------------------
Writes all system events to logs/system_events.log and displays
color-coded messages in the terminal for real-time monitoring.
"""

import os
from datetime import datetime

# ✅ Ensure logs folder exists
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_events.log")

# ✅ Terminal color codes
COLORS = {
    "INFO": "\033[94m",     # Blue
    "SUCCESS": "\033[92m",  # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",    # Red
    "RESET": "\033[0m",     # Reset
}

def log_event(module: str, status: str, message: str):
    """
    Save an event entry to logs/system_events.log and print it color-coded.
    Example:
        log_event("GoogleSheetsSync", "SUCCESS", "Added new hotel to sheet")
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize status to uppercase
    status = status.upper().strip()

    # Pick color for the console output
    color = COLORS.get("SUCCESS") if status in ("SUCCESS", "SYNCED") else (
        COLORS.get("WARNING") if status in ("SKIPPED", "PENDING") else (
            COLORS.get("ERROR") if status == "ERROR" else COLORS.get("INFO")
        )
    )

    # Format the log entry
    line = f"[{timestamp}] {module} | {status} | {message}"
    colored_line = f"{color}{line}{COLORS['RESET']}"

    # Write to file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    # Print to console
    print(colored_line)
