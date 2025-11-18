# -*- coding: utf-8 -*-
"""
hotel_info.py – Guzo Guest Assist Hotel Information Module (v6.5)
-----------------------------------------------------------------
Provides structured bilingual hotel details and helper functions
for professional, natural guest conversations.
"""

def get_all_hotels() -> list:
    """Return all registered hotel names."""
    return ["Sofi Hotel", "Aron Luxury Hotel"]


def fetch_hotel_info(hotel_name: str) -> dict:
    """Return structured hotel information by name."""
    hotels = {
        "Sofi Hotel": {
            "Location": "Addis Ababa, Bole area – near Edna Mall",
            "Description": "Modern city hotel with deluxe rooms, rooftop restaurant, and airport shuttle service.",
            "Phone": "+251 911 234 567",
            "Email": "reservation@sofihotel.com",
            "Check-In": "2:00 PM",
            "Check-Out": "12:00 PM",
            "Amenities": ["Free Wi-Fi", "Breakfast Buffet", "Airport Transfer", "24h Room Service"],
        },
        "Aron Luxury Hotel": {
            "Location": "Bole Road, Addis Ababa",
            "Description": "Five-star comfort with spa, heated pool, and panoramic Sky Lounge Restaurant.",
            "Phone": "+251 922 334 455",
            "Email": "info@aronluxuryhotel.com",
            "Check-In": "2:00 PM",
            "Check-Out": "12:00 PM",
            "Amenities": ["Free Wi-Fi", "Buffet Breakfast", "Spa & Sauna", "Airport Shuttle"],
        },
    }
    return hotels.get(hotel_name.strip().title())


def build_hotel_overview(hotel_data: dict, lang: str = "en") -> str:
    """Return a bilingual formatted overview of hotel details."""
    if not hotel_data:
        return "⚠️ Hotel information not found. የሆቴል መረጃ አልተገኘም።"

    if lang == "am":
        return (
            f"🏨 ስፍራ፡ {hotel_data['Location']}\n"
            f"📞 ስልክ፡ {hotel_data['Phone']}\n"
            f"📧 ኢሜል፡ {hotel_data['Email']}\n"
            f"🕓 መግቢያ፡ {hotel_data['Check-In']}፣ መውጫ፡ {hotel_data['Check-Out']}\n"
            f"💬 መግለጫ፡ {hotel_data['Description']}\n"
        )

    return (
        f"🏨 Location: {hotel_data['Location']}\n"
        f"📞 Phone: {hotel_data['Phone']}\n"
        f"📧 Email: {hotel_data['Email']}\n"
        f"🕓 Check-In: {hotel_data['Check-In']} | Check-Out: {hotel_data['Check-Out']}\n"
        f"💬 Description: {hotel_data['Description']}\n"
    )


def build_hotel_recommendations(location_keyword: str, lang: str = "en") -> str:
    """Return hotels that match a given location keyword."""
    hotels_by_location = {
        "Sofi Hotel": "Bole",
        "Aron Luxury Hotel": "Bole",
    }
    results = [name for name, loc in hotels_by_location.items() if location_keyword.lower() in loc.lower()]

    if not results:
        return "⚠️ No hotels found for that area. ምንም ሆቴሎች አልተገኙም።"

    joined = ", ".join(results)
    if lang == "am":
        return f"🏨 በ {location_keyword} ያሉ የሚመከሩ ሆቴሎች፡ {joined}"
    return f"🏨 Recommended hotels near {location_keyword}: {joined}"
