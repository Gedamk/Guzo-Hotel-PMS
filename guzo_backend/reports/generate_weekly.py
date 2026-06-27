# guzo_backend/reports/generate_weekly.py

"""
Guzo – Weekly Room Division Report Generator

Usage (called from shell script):

    python -m guzo_backend.reports.generate_weekly \
        --start 2025-11-17 \
        --end 2025-11-23 \
        --pdf reports/weekly_2025-11-17_to_2025-11-23.pdf \
        --excel reports/weekly_2025-11-17_to_2025-11-23.xlsx
"""

import argparse
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate WEEKLY Guzo report")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--pdf", required=True, help="Output PDF path")
    parser.add_argument("--excel", required=True, help="Output Excel path")
    return parser.parse_args()


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def build_weekly_report(start: date, end: date, pdf_path: str, excel_path: str) -> None:
    """
    TODO: Implement REAL logic here:
      - Query PostgreSQL bookings for [start, end]
      - Aggregate KPIs (occupancy, ADR, RevPAR, room nights, revenue)
      - Export Excel and PDF

    For now, we just log so pipeline is wired correctly.
    """
    logger.info("🔧 [STUB] build_weekly_report(): %s → %s", start, end)
    logger.info("🔧 [STUB] Would write PDF to:   %s", pdf_path)
    logger.info("🔧 [STUB] Would write Excel to: %s", excel_path)

    # Minimal placeholder: create empty files so nothing breaks
    for path in (pdf_path, excel_path):
        with open(path, "wb") as f:
            f.write(b"")  # empty file placeholder

    logger.info("✅ [STUB] Weekly report placeholder files created.")


def main() -> None:
    args = parse_args()
    start = to_date(args.start)
    end = to_date(args.end)

    logger.info("📊 Generating WEEKLY report: %s → %s", start, end)
    build_weekly_report(start, end, args.pdf, args.excel)


if __name__ == "__main__":
    main()
