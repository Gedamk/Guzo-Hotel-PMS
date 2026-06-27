# guzo_backend/reports/generate_monthly.py

"""
Guzo – Monthly Room Division Report Generator

Usage:

    python -m guzo_backend.reports.generate_monthly \
        --year 2025 \
        --month 11 \
        --pdf reports/monthly_2025-11.pdf \
        --excel reports/monthly_2025-11.xlsx
"""

import argparse
import logging
from datetime import date
from calendar import monthrange

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MONTHLY Guzo report")
    parser.add_argument("--year", type=int, required=True, help="Year, e.g. 2025")
    parser.add_argument("--month", type=int, required=True, help="Month 1-12")
    parser.add_argument("--pdf", required=True, help="Output PDF path")
    parser.add_argument("--excel", required=True, help="Output Excel path")
    return parser.parse_args()


def month_range(year: int, month: int) -> tuple[date, date]:
    """Return first and last day of the month."""
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def build_monthly_report(year: int, month: int, pdf_path: str, excel_path: str) -> None:
    """
    TODO: Implement REAL logic here:
      - Query PostgreSQL for that entire month
      - Aggregate by property, by segment, etc.
      - Export professional PDF + Excel

    For now, just create empty files.
    """
    start, end = month_range(year, month)
    logger.info("🔧 [STUB] build_monthly_report(): %s → %s", start, end)
    logger.info("🔧 [STUB] Would write PDF to:   %s", pdf_path)
    logger.info("🔧 [STUB] Would write Excel to: %s", excel_path)

    for path in (pdf_path, excel_path):
        with open(path, "wb") as f:
            f.write(b"")

    logger.info("✅ [STUB] Monthly report placeholder files created.")


def main() -> None:
    args = parse_args()
    logger.info("📊 Generating MONTHLY report: %04d-%02d", args.year, args.month)
    build_monthly_report(args.year, args.month, args.pdf, args.excel)


if __name__ == "__main__":
    main()
