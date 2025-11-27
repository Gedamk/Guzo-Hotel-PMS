#!/usr/bin/env bash

# --------------------------------------------------------
# Guzo – Weekly Report Generator
# --------------------------------------------------------

set -e  # stop on first error

echo "Starting WEEKLY report generation..."

# Always work from project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/Scripts/activate

# Compute last Monday → next Sunday range
WEEK_START=$(date -d "last monday" +"%Y-%m-%d")
WEEK_END=$(date -d "next sunday" +"%Y-%m-%d")

REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"

PDF_PATH="$REPORT_DIR/weekly_${WEEK_START}_to_${WEEK_END}.pdf"
XLSX_PATH="$REPORT_DIR/weekly_${WEEK_START}_to_${WEEK_END}.xlsx"

echo "Week range: $WEEK_START → $WEEK_END"

python -m guzo_backend.reports.generate_weekly \
  --start "$WEEK_START" \
  --end "$WEEK_END" \
  --pdf "$PDF_PATH" \
  --excel "$XLSX_PATH"

echo "Weekly report generation finished."

