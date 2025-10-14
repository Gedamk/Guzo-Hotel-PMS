# log_helper.py
import os
import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "all_jobs.log")

def log_event(job_name: str, status: str, message: str = ""):
    """Append an event line to the main automation log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {job_name}: {status}"
    if message:
        line += f" - {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)
