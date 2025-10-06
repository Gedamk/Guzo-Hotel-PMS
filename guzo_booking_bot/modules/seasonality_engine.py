"""
Seasonality Engine
Analyzes booking trends, occupancy, and seasonality
to trigger dynamic special offers for both international
and Ethiopian hospitality markets, with manual override support.
"""

from datetime import datetime
import random
import os

# ============================
# Season Definitions
# ============================

def get_international_season():
    """Return current international season (by month)."""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "Winter Festive Season"
    elif month in [3, 4, 5]:
        return "Spring Travel Season"
    elif month in [6, 7, 8]:
        return "Summer Holiday Peak"
    else:
        return "Autumn Business Travel"


def get_ethiopian_season():
    """Return current Ethiopian season (traditional calendar mapping)."""
    month = datetime.now().month
    if month in [6, 7, 8, 9]:       # June–September
        return "Kiremt (Rainy Season)"
    elif month in [10, 11, 12, 1]:  # October–January
        return "Bega (Dry & Festive Season)"
    else:                           # February–May
        return "Belg (Short Rains)"


def get_season_context():
    """Return both international and Ethiopian season context."""
    return get_international_season(), get_ethiopian_season()


# ============================
# Demand Analysis
# ============================

def analyze_demand(occupancy_rate):
    """Decide discount level based on occupancy."""
    if occupancy_rate < 40:
        return random.choice([25, 30, 35])  # Deep discount
    elif occupancy_rate < 70:
        return random.choice([10, 15, 20])  # Moderate discount
    else:
        return 0  # High demand, no discount


# ============================
# Offer Generator
# ============================

def generate_offer(hotel_name, occupancy_rate):
    """
    Generate a dynamic seasonal offer.
    Allows manual override using .env settings.
    Returns None if no discount applies.
    """
    intl_season, eth_season = get_season_context()
    discount = analyze_demand(occupancy_rate)
    valid_until = datetime.now().strftime("%Y-%m-%d")
    source = "auto"

    # ---- Manual Overrides from .env ----
    override_intl = os.getenv("FORCE_SEASON_INTL", "").strip()
    override_eth = os.getenv("FORCE_SEASON_ETH", "").strip()
    override_discount = os.getenv("FORCE_DISCOUNT", "").strip()
    override_valid = os.getenv("FORCE_VALID_UNTIL", "").strip()

    if override_intl:
        intl_season = override_intl
        source = "override"
    if override_eth:
        eth_season = override_eth
        source = "override"
    if override_discount:
        try:
            discount = int(override_discount)
            source = "override"
        except ValueError:
            print(f"⚠️ Invalid FORCE_DISCOUNT value: {override_discount}")
    if override_valid:
        valid_until = override_valid
        source = "override"

    # Skip if no discount at all
    if discount == 0:
        return None

    return {
        "hotel_name": hotel_name,
        "offer_title": f"{eth_season} / {intl_season} Special Offer",
        "offer_discount": discount,
        "offer_valid_until": valid_until,
        "intl_season": intl_season,
        "eth_season": eth_season,
        "source": source  # Track if auto-generated or forced
    }
