# -*- coding: utf-8 -*-
"""
test_env_sendgrid.py – .env and SendGrid key verification
----------------------------------------------------------
Detects the active .env file, checks for SENDGRID_API_KEY,
and logs the result to logs/system_events.log.
"""

import os
from datetime import datetime
from dotenv import find_dotenv, load_dotenv

# === Helper: Write to logs/system_events.log ===
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_events.log")

def log_event(module: str, status: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {module} | {status} | {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

# === Step 1: Detect .env file ===
env_path = find_dotenv(usecwd=True)
if env_path:
    print(f"Detected .env file path: {env_path}")
    load_dotenv(env_path, override=True)
else:
    print("❌ No .env file found")
    log_event("test_env_sendgrid", "ERROR", "No .env file detected")
    exit()

# === Step 2: Check SENDGRID_API_KEY ===
key = os.getenv("SENDGRID_API_KEY")

if key:
    prefix = key[:10]
    length = len(key)
    print(f"Key prefix: {prefix}")
    print(f"Key length: {length}")
    log_event("test_env_sendgrid", "OK", f"SENDGRID key loaded successfully (len={length})")
else:
    print("❌ SENDGRID_API_KEY not found in .env file")
    log_event("test_env_sendgrid", "ERROR", "SENDGRID_API_KEY not found")

