#!/usr/bin/bash

YEAR="$1"
MONTH="$2"

if [ -z "$YEAR" ] || [ -z "$MONTH" ]; then
  echo "Usage: ./run_reports_month.sh YEAR MONTH"
  echo "Example: ./run_reports_month.sh 2025 11"
  exit 1
fi

BASE_URL="http://127.0.0.1:8000"
AUTH="Authorization: Bearer <REDACTED_DEMO_BEARER_TOKEN>"

echo "=== Portfolio – all hotels for $YEAR-$MONTH ==="
curl -s -H "$AUTH" \
  "$BASE_URL/reports/portfolio?year=$YEAR&month=$MONTH" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

echo "=== Dream Big Hotel – DRE001 ($YEAR-$MONTH) ==="
curl -s -H "$AUTH" \
  "$BASE_URL/reports/hotel?property_code=DRE001&year=$YEAR&month=$MONTH" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

echo "=== N&N Luxury Hotel – NN002 ($YEAR-$MONTH) ==="
curl -s -H "$AUTH" \
  "$BASE_URL/reports/hotel?property_code=NN002&year=$YEAR&month=$MONTH" \
  | python -m json.tool

echo ""
echo "============= DONE ============="
