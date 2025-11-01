# -*- coding: utf-8 -*-
"""
Secure Logger
Provides a centralized logger with secret masking.
All sensitive environment values are automatically redacted from logs.
"""

import logging
import os

# ==============================
# Sensitive Keys to Mask
# ==============================
SENSITIVE_KEYS = [
    "STRIPE_SECRET_KEY",
    "SENDGRID_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "GMAIL_PASSWORD",
    "DATABASE_URL"
]

class SecretFilter(logging.Filter):
    """Mask sensitive values in log output."""
    def filter(self, record):
        msg = str(record.getMessage())
        for key in SENSITIVE_KEYS:
            val = os.getenv(key)
            if val and val in msg:
                msg = msg.replace(val, "***")
        record.msg = msg
        return True

# ==============================
# Logger Factory
# ==============================
def get_logger(name="GuzoGuestAssist", log_file="logs/system.log"):
    """
    Returns a secure logger with both console + file handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:  # prevent adding handlers twice
        return logger

    logger.setLevel(logging.INFO)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # File Handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Add secret filter
    ch.addFilter(SecretFilter())
    fh.addFilter(SecretFilter())

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger
