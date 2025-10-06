# -*- coding: utf-8 -*-
"""
Retry Logs Runner
Runs the retry handler process for failed notifications.
"""

import sys
from guzo_booking_bot.modules import retry_handler


def safe_print(msg: str):
    """Print safely without breaking pytest or stdout capture."""
    try:
        print(msg, flush=True)
    except Exception:
        try:
            sys.stderr.write(msg + "\n")
        except Exception:
            pass  # absolute fallback


def main():
    try:
        safe_print("[INFO] Starting retry log runner...")
        retry_handler.retry_failed_notifications()
        safe_print("[OK] Retry process finished.")
    except Exception as e:
        try:
            sys.stderr.write(f"[FAIL] Retry runner crashed: {e}\n")
        except Exception:
            pass


if __name__ == "__main__":
    main()
