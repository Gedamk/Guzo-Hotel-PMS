#!/usr/bin/env python3
"""
Cleanup Sheets
- Resets booking sheet for clean testing/demo
"""

import sys, os, logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from guzo_booking_bot.modules.booking import reset_sheet

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Ã°ÂÂ§Â¹ Resetting booking sheet...")
        reset_sheet()
        logger.info("Ã¢ÂÂ Booking sheet reset complete.")
    except Exception as e:
        logger.error(f"Ã¢ÂÂ Reset failed: {e}")

if __name__ == "__main__":
    main()
