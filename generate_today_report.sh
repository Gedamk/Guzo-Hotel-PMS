#!/usr/bin/env bash
# Generate today's Guzo Room Division Daily Report (PDF + Excel)

set -e

# Always run from the project root
cd "$(dirname "$0")"

# Activate virtualenv
if [ -f "venv/Scripts/activate" ]; then
  # Git Bash on Windows
  source venv/Scripts/activate
fi

# Today in YYYY-MM-DD (business date)
TODAY=$(date +%F)
echo "�� Generating daily report for: $TODAY"

# PDF
curl -o "daily-$TODAY.pdf" \
  "http://127.0.0.1:8000/reports/daily/pdf?business_date=$TODAY" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# Excel (CSV with Excel mime-type)
curl -o "daily-$TODAY.xlsx" \
  "http://127.0.0.1:8000/reports/daily/excel?business_date=$TODAY" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

echo "✅ Done. Files saved as:"
echo "   - daily-$TODAY.pdf"
echo "   - daily-$TODAY.xlsx"
