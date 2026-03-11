"""Travel information tools — weather, currency, trip details."""

import json
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.tools import tool


# Mock travel data for Finland trip
FINLAND_TRIP = {
    "destination": "Helsinki, Finland",
    "country_code": "FI",
    "departure_date": "2026-03-13",
    "return_date": "2026-03-17",
    "days_until_trip": 3,  # Will be calculated dynamically
    "flight_out": {
        "airline": "Finnair",
        "flight": "AY 6142",
        "departure": "2026-03-13T16:30:00-06:00",
        "arrival": "2026-03-14T11:15:00+02:00",
        "route": "Austin (AUS) → Helsinki (HEL)",
        "seat": "14A (window)",
        "confirmation": "AY7829104"
    },
    "flight_return": {
        "airline": "Finnair",
        "flight": "AY 6143",
        "departure": "2026-03-17T13:45:00+02:00",
        "arrival": "2026-03-17T18:20:00-06:00",
        "route": "Helsinki (HEL) → Austin (AUS)"
    },
    "hotel": {
        "name": "Hotel Kämp",
        "address": "Pohjoisesplanadi 29, 00100 Helsinki",
        "check_in": "2026-03-14T15:00:00+02:00",
        "check_out": "2026-03-17T12:00:00+02:00",
        "rate": "€285/night",
        "confirmation": "HK-2026-78291",
        "amenities": ["WiFi", "Spa", "Fitness Center", "Kämp Bar", "Breakfast included"]
    },
    "activities": [
        {"date": "2026-03-15", "name": "Northern Lights Tour", "time": "8:00 PM - 2:00 AM", "booking": "VFT-2026-4821"},
        {"date": "2026-03-16", "name": "Suomenlinna Sea Fortress", "time": "10:00 AM"},
        {"date": "2026-03-16", "name": "Finnish Sauna Experience", "time": "5:00 PM"}
    ]
}

# Mock weather data
WEATHER_DATA = {
    "austin": {
        "current": {"temp_c": 22, "temp_f": 72, "condition": "Partly Cloudy", "humidity": 45, "wind_kph": 15},
        "forecast": [
            {"date": "2026-03-10", "high_c": 24, "low_c": 14, "condition": "Sunny"},
            {"date": "2026-03-11", "high_c": 26, "low_c": 15, "condition": "Sunny"},
            {"date": "2026-03-12", "high_c": 23, "low_c": 13, "condition": "Partly Cloudy"},
            {"date": "2026-03-13", "high_c": 21, "low_c": 12, "condition": "Cloudy"},
        ]
    },
    "helsinki": {
        "current": {"temp_c": -2, "temp_f": 28, "condition": "Light Snow", "humidity": 85, "wind_kph": 20},
        "forecast": [
            {"date": "2026-03-13", "high_c": 0, "low_c": -5, "condition": "Cloudy"},
            {"date": "2026-03-14", "high_c": 2, "low_c": -3, "condition": "Partly Cloudy"},
            {"date": "2026-03-15", "high_c": -1, "low_c": -8, "condition": "Clear ✨", "aurora_chance": "High (Kp 4-5)"},
            {"date": "2026-03-16", "high_c": 1, "low_c": -4, "condition": "Light Snow"},
            {"date": "2026-03-17", "high_c": 3, "low_c": -2, "condition": "Partly Cloudy"},
        ]
    }
}

# Currency exchange rates (mock)
CURRENCY_DATA = {
    "EUR": {"rate": 0.92, "name": "Euro", "symbol": "€"},
    "GBP": {"rate": 0.79, "name": "British Pound", "symbol": "£"},
    "JPY": {"rate": 149.50, "name": "Japanese Yen", "symbol": "¥"},
    "SEK": {"rate": 10.45, "name": "Swedish Krona", "symbol": "kr"},
}


@tool
def get_upcoming_trip() -> str:
    """Get details about Mike's upcoming trip including flights, hotel, and activities.
    Returns comprehensive trip information for the nearest upcoming trip."""
    
    # Calculate days until trip
    trip_date = datetime(2026, 3, 13)
    today = datetime(2026, 3, 10)  # Mock "today" for demo
    days_until = (trip_date - today).days
    
    trip_info = {
        **FINLAND_TRIP,
        "days_until_trip": days_until,
        "status": "upcoming" if days_until > 0 else "in_progress",
        "packing_tips": [
            "Thermal layers — temps around -5°C to 2°C",
            "Warm waterproof jacket",
            "Hat, gloves, scarf",
            "Camera with tripod for Northern Lights",
            "Comfortable walking shoes",
            "Power adapter (Type C/F plugs)"
        ],
        "useful_phrases": {
            "Hello": "Hei (hay)",
            "Thank you": "Kiitos (kee-tos)",
            "Cheers!": "Kippis! (kip-pis)",
            "Excuse me": "Anteeksi (ahn-tek-si)"
        }
    }
    
    return json.dumps(trip_info, indent=2)


@tool
def get_weather(city: str, include_forecast: bool = True) -> str:
    """Get current weather and forecast for a city.
    Supports: austin, helsinki. Returns temperature, conditions, and multi-day forecast."""
    
    city_key = city.lower().strip()
    if city_key not in WEATHER_DATA:
        return json.dumps({"error": f"Weather data not available for {city}. Try 'austin' or 'helsinki'."})
    
    data = WEATHER_DATA[city_key]
    result = {
        "city": city.title(),
        "current": data["current"],
    }
    
    if include_forecast:
        result["forecast"] = data["forecast"]
    
    return json.dumps(result, indent=2)


@tool
def get_currency_exchange(from_currency: str = "USD", to_currency: str = "EUR", amount: float = 100) -> str:
    """Get currency exchange rate and convert an amount.
    Default converts USD to EUR. Supports: EUR, GBP, JPY, SEK."""
    
    to_upper = to_currency.upper()
    if to_upper not in CURRENCY_DATA:
        return json.dumps({"error": f"Currency {to_currency} not supported. Try: EUR, GBP, JPY, SEK"})
    
    rate_info = CURRENCY_DATA[to_upper]
    converted = round(amount * rate_info["rate"], 2)
    
    return json.dumps({
        "from": from_currency.upper(),
        "to": to_upper,
        "rate": rate_info["rate"],
        "amount": amount,
        "converted": converted,
        "formatted": f"{rate_info['symbol']}{converted:,.2f}",
        "currency_name": rate_info["name"],
        "tip": "Finland uses Euro (€). Credit cards widely accepted. Tipping not expected but appreciated."
    }, indent=2)


@tool
def get_travel_checklist(destination: str = "finland") -> str:
    """Get a travel checklist and tips for a destination.
    Currently supports: finland."""
    
    if destination.lower() != "finland":
        return json.dumps({"error": "Checklist only available for Finland currently."})
    
    return json.dumps({
        "destination": "Finland",
        "documents": [
            "✓ Valid passport (no visa needed for US citizens < 90 days)",
            "✓ Flight confirmation (AY7829104)",
            "✓ Hotel reservation (HK-2026-78291)",
            "✓ Travel insurance (recommended)",
            "✓ Northern Lights tour booking (VFT-2026-4821)"
        ],
        "packing": {
            "clothing": [
                "Thermal base layers",
                "Warm fleece/sweater",
                "Waterproof winter jacket",
                "Warm hat covering ears",
                "Insulated gloves",
                "Scarf/neck gaiter",
                "Warm socks (wool)",
                "Waterproof boots"
            ],
            "electronics": [
                "Camera + tripod (for aurora)",
                "Extra batteries (cold drains them fast)",
                "Power adapter (Type C/F)",
                "Portable charger"
            ],
            "essentials": [
                "Sunglasses (snow glare)",
                "Lip balm & moisturizer",
                "Hand warmers",
                "Small backpack for day trips"
            ]
        },
        "tips": [
            "🌡️ Expect temps from -8°C to 2°C (18°F to 36°F)",
            "🌌 Best aurora viewing: March 15 (clear skies forecast)",
            "💳 Cards accepted everywhere, cash rarely needed",
            "🧖 Don't miss the Finnish sauna experience!",
            "☕ Finns drink the most coffee per capita — try local cafes",
            "🍺 Craft beer scene is excellent — try Bryggeri Helsinki"
        ],
        "emergency": {
            "emergency_number": "112",
            "us_embassy": "+358 9 616 250",
            "hotel_phone": "+358 9 576 111"
        }
    }, indent=2)


# All travel tools for easy import
travel_tools = [
    get_upcoming_trip,
    get_weather,
    get_currency_exchange,
    get_travel_checklist,
]
