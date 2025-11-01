# guzo_backend/modules/security.py
"""
Security Utilities
Handles API key validation, masking logs, and future encryption.
"""

import os
from hashlib import sha256

def mask_secret(secret, visible=4):
    """Return masked version of a secret (keep last `visible` chars)."""
    if not secret:
        return ""
    return "*" * (len(secret) - visible) + secret[-visible:]

def validate_env_vars():
    """Check critical env variables exist."""
    critical = ["SENDGRID_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]
    missing = [var for var in critical if not os.getenv(var)]
    return missing

def hash_guest_data(guest_name, contact):
    """Hash guest data for anonymized analytics."""
    return sha256(f"{guest_name}-{contact}".encode()).hexdigest()
