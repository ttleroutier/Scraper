"""Geocoding (OpenStreetMap Nominatim) and distance helpers."""

import math
import requests

from config import USER_AGENT, HTTP_TIMEOUT

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


# ------------------------------------------------------- 1. GEOCODING
def geocode_address(address: str):
    """Return (lat, lon, display_name) or None."""
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        first = results[0]
        return float(first["lat"]), float(first["lon"]), first["display_name"]
    except Exception:
        return None


# -------------------------------------------------------- 2. DISTANCE
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in kilometres."""
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


# ------------------------------------------- 3. RADIUS -> MAP ZOOM LEVEL
def zoom_for_radius(radius_km: float) -> int:
    """Rough mapping so the Maps viewport covers the requested radius."""
    thresholds = [(1, 15), (2, 14), (5, 13), (10, 12), (20, 11), (50, 10)]
    for limit, zoom in thresholds:
        if radius_km <= limit:
            return zoom
    return 9
