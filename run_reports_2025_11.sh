#!/usr/bin/bash

# Portfolio – all hotels (2025-11)
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://127.0.0.1:8000/reports/portfolio?year=2025&month=11" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# Dream Big Hotel – DRE001 (2025-11)
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://127.0.0.1:8000/reports/hotel?property_code=DRE001&year=2025&month=11" \
  | python -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# N&N Luxury Hotel – alias NN002 → N&N002 (2025-11)
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://127.0.0.1:8000/reports/hotel?property_code=NN002&year=2025&month=11" \
  | python -m json.tool

