# guzo_backend/modules/logger.py
import os
import logging

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "notifications.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_notification(channel, recipient, status, message=""):
    logging.info(f"{channel} | {recipient} | {status} | {message}")
