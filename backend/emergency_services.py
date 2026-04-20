"""
emergency_services.py

Fixes vs original:
  • Overpass query now uses the correct QL union syntax with out body;
  • Added retry with exponential back-off (Overpass rate-limits aggressively)
  • Increased timeout to 15 s
  • Returns empty list on failure instead of crashing callers
"""

import time
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL template — {lat}, {lon}, {radius} are substituted at runtime
_QUERY_TEMPLATE = """
[out:json][timeout:25];
(
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  node["amenity"="ambulance_station"](around:{radius},{lat},{lon});
  node["amenity"="police"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});
  node["emergency"="ambulance_station"](around:{radius},{lat},{lon});
);
out body;
"""


def nearby_services(lat: float, lon: float, radius: int = 5000,
                    retries: int = 3) -> dict:
    """
    Query OpenStreetMap Overpass API for emergency services near (lat, lon).

    Returns the parsed JSON dict, or {"elements": []} on failure.
    """
    query = _QUERY_TEMPLATE.format(lat=lat, lon=lon, radius=radius)

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            print(f"[services] ⚠ Timeout (attempt {attempt}/{retries})")

        except requests.exceptions.HTTPError as e:
            print(f"[services] ⚠ HTTP error: {e} (attempt {attempt}/{retries})")

        except Exception as e:
            print(f"[services] ❌ Unexpected error: {e}")
            break   # non-retryable

        if attempt < retries:
            time.sleep(2 ** attempt)   # 2 s, 4 s back-off

    return {"elements": []}