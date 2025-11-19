#!/usr/bin/bash

YEAR="$1"
MONTH="$2"

if [ -z "$YEAR" ] || [ -z "$MONTH" ]; then
  echo "Usage: ./export_reports_month.sh YEAR MONTH"
  echo "Example: ./export_reports_month.sh 2025 11"
  exit 1
fi

BASE_URL="http://127.0.0.1:8000"
AUTH="Authorization: Bearer <REDACTED_DEMO_BEARER_TOKEN>"

FOLDER="reports/${YEAR}_${MONTH}"
mkdir -p "$FOLDER"

echo "Saving reports into: $FOLDER"

# Portfolio raw + pretty
curl -s -H "$AUTH" \
  "$BASE_URL/reports/portfolio?year=$YEAR&month=$MONTH" \
  > "${FOLDER}/portfolio_${YEAR}_${MONTH}.json"

cat "${FOLDER}/portfolio_${YEAR}_${MONTH}.json" \
  | python -m json.tool \
  > "${FOLDER}/portfolio_${YEAR}_${MONTH}_pretty.json"

# Dream Big – DRE001
curl -s -H "$AUTH" \
  "$BASE_URL/reports/hotel?property_code=DRE001&year=$YEAR&month=$MONTH" \
  > "${FOLDER}/hotel_DRE001_${YEAR}_${MONTH}.json"

cat "${FOLDER}/hotel_DRE001_${YEAR}_${MONTH}.json" \
  | python -m json.tool \
  > "${FOLDER}/hotel_DRE001_${YEAR}_${MONTH}_pretty.json"

# N&N – NN002
curl -s -H "$AUTH" \
  "$BASE_URL/reports/hotel?property_code=NN002&year=$YEAR&month=$MONTH" \
  > "${FOLDER}/hotel_NN002_${YEAR}_${MONTH}.json"

cat "${FOLDER}/hotel_NN002_${YEAR}_${MONTH}.json" \
  | python -m json.tool \
  > "${FOLDER}/hotel_NN002_${YEAR}_${MONTH}_pretty.json"

echo "Done. Files saved in $FOLDER"
