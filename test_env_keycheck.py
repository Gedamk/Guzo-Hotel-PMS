# -*- coding: utf-8 -*-
"""
test_env_keycheck.py – verifies SendGrid .env variables are loading correctly
"""

import os
from dotenv import load_dotenv

# Load .env file
dotenv_path = r"C:\Users\Gedan\Desktop\Guzo\.env"
load_dotenv(dotenv_path=dotenv_path)

print("✅ Testing environment file:", dotenv_path)
print("SENDGRID_API_KEY loaded:", bool(os.getenv("SENDGRID_API_KEY")))
print("DEFAULT_SENDER_EMAIL:", os.getenv("DEFAULT_SENDER_EMAIL"))
print("TEST_EMAIL:", os.getenv("TEST_EMAIL"))
