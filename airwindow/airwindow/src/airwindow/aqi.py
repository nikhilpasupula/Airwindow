"""AQI categories (US EPA scale, which is what Open-Meteo `us_aqi` and aqicn report)."""

_BANDS = [
    (50, "good"),
    (100, "moderate"),
    (150, "sensitive"),
    (200, "unhealthy"),
    (300, "very_unhealthy"),
]


def category(aqi: float) -> str:
    """Return the category key for an AQI value."""
    for upper, name in _BANDS:
        if aqi <= upper:
            return name
    return "hazardous"
