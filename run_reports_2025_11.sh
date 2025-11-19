#!/usr/bin/bash

# Portfolio – all hotels
curl -H "Authorization: Bearer <REDACTED_DEMO_BEARER_TOKEN>" \
  "http://127.0.0.1:8000/reports/portfolio?year=2025&month=11" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# Dream Big Hotel – DRE001
curl -H "Authorization: Bearer <REDACTED_DEMO_BEARER_TOKEN>" \
  "http://127.0.0.1:8000/reports/hotel?property_code=DRE001&year=2025&month=11" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# N&N Luxury Hotel – using friendly alias NN002
curl -H "Authorization: Bearer <REDACTED_DEMO_BEARER_TOKEN>" \
  "http://127.0.0.1:8000/reports/hotel?property_code=NN002&year=2025&month=11" \
  | python -m json.tool

