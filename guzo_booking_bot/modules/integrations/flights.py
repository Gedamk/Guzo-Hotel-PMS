# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ« Guzo Guest Assist ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Flight Data Integration (v1.0)
-----------------------------------------------------
Fetches Ethiopian Airlines domestic & international flight data
using the AviationStack API and caches results locally.

ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Designed for dashboard use
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Ethiopian-friendly formatting (ADD hub)
ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Works offline with local cache fallback
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
CACHE_PATH = os.path.join("storage", "flights.json")

def get_flight_data(limit=10):
    """Fetch recent Ethiopian Airlines flights (departures & arrivals)."""
    if not API_KEY:
        return {"error": "Missing API key. Add AVIATIONSTACK_API_KEY to .env"}

    try:
        url = (
            "http://api.aviationstack.com/v1/flights"
            f"?access_key={API_KEY}"
            "&airline_iata=ET"  # Ethiopian Airlines
            "&limit={limit}"
        )
        response = requests.get(url, timeout=8)
        data = response.json()

        if "error" in data:
            return {"error": data["error"].get("message", "API Error")}

        flights = []
        for f in data.get("data", []):
            flights.append({
                "flight": f["flight"]["iata"] if f.get("flight") else "N/A",
                "departure": f["departure"]["airport"] if f.get("departure") else "",
                "arrival": f["arrival"]["airport"] if f.get("arrival") else "",
                "status": f.get("flight_status", "unknown").capitalize(),
                "scheduled": f["departure"].get("scheduled") if f.get("departure") else "",
                "aircraft": f.get("aircraft", {}).get("registration", ""),
            })

        # Cache for offline view
        os.makedirs("storage", exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "flights": flights}, f, indent=2)

        return flights

    except Exception as e:
        # Load from cache if available
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("flights", [])
        return {"error": str(e)}

def get_cached_flights():
    """Return cached flight data if recent (less than 3 hours old)."""
    if not os.path.exists(CACHE_PATH):
        return []
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        ts = datetime.fromisoformat(cache.get("timestamp", "1970-01-01"))
        if datetime.now() - ts < timedelta(hours=3):
            return cache.get("flights", [])
        return []
    except Exception:
        return []

if __name__ == "__main__":
    data = get_flight_data()
    print(json.dumps(data[:3], indent=2, ensure_ascii=False))
