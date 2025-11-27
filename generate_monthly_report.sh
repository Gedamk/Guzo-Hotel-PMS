#!/usr/bin/env bash

# --------------------------------------------------------
# Guzo – Monthly Report Generator
# --------------------------------------------------------

set -e

echo "Starting MONTHLY report generation..."

cd "$(dirname "$0")"
source venv/Scripts/activate

YEAR=$(date +"%Y")
MONTH=$(date +"%m")

REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"

PDF_PATH="$REPORT_DIR/monthly_${YEAR}-${MONTH}.pdf"
XLSX_PATH="$REPORT_DIR/monthly_${YEAR}-${MONTH}.xlsx"

echo "Month: $YEAR-$MONTH"

python -m guzo_backend.reports.generate_monthly \
  --year "$YEAR" \
  --month "$MONTH" \
  --pdf "$PDF_PATH" \
  --excel "$XLSX_PATH"

echo "Monthly report generation finished."

