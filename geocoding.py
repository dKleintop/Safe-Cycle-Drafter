"""geocoding.py - Fast location autofill catalog and live OpenStreetMap geocoding.

Advanced technique notes:
- Uses `functools.lru_cache` memoization (beyond CS1) to cache remote
  OpenStreetMap Nominatim/Photon responses so repeated lookups avoid latency.
- Pre-indexes `CYCLING_LOCATIONS` into an O(1) lowercase lookup dictionary for
  instant address resolution without linear scans on every render.
- Detects the browser Pyodide runtime (`pyodide.http.open_url`) with a local
  `urllib.request` fallback so live address lookup works both in-browser and
  in local Python without external dependencies.
"""

import functools
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from models import Coordinate

CYCLING_LOCATIONS: List[Dict[str, Any]] = [
    {
        "name": "Louis Redding Hall, Newark, DE",
        "city": "Newark, DE",
        "category": "Campus Corridor",
        "lat": 39.676456,
        "lon": -75.747050,
    },
    {
        "name": "Kirkwood, DE",
        "city": "Kirkwood, DE",
        "category": "Trail Endpoint",
        "lat": 39.571807,
        "lon": -75.696079,
    },
    {
        "name": "University of Delaware, Newark, DE",
        "city": "Newark, DE",
        "category": "Campus Corridor",
        "lat": 39.678044,
        "lon": -75.750668,
    },
    {
        "name": "Glasgow Park, Newark, DE",
        "city": "Newark, DE",
        "category": "Park Route",
        "lat": 39.610684,
        "lon": -75.729030,
    },
    {
        "name": "Lums Pond State Park, DE",
        "city": "Kirkwood, DE",
        "category": "Park Route",
        "lat": 39.559389,
        "lon": -75.719335,
    },
    {
        "name": "Wilmington Riverfront, DE",
        "city": "Wilmington, DE",
        "category": "Greenway Path",
        "lat": 39.734842,
        "lon": -75.556214,
    },
    {
        "name": "Central Park South, New York, NY",
        "city": "New York, NY",
        "category": "Park Route",
        "lat": 40.7661,
        "lon": -73.9772,
    },
    {
        "name": "Brooklyn Bridge (Manhattan Side), NY",
        "city": "New York, NY",
        "category": "Bridge Bikeway",
        "lat": 40.7126,
        "lon": -74.0048,
    },
    {
        "name": "Hudson River Greenway at 72nd St, NY",
        "city": "New York, NY",
        "category": "Greenway Path",
        "lat": 40.7818,
        "lon": -73.9877,
    },
    {
        "name": "Hudson River Greenway at Battery Park, NY",
        "city": "New York, NY",
        "category": "Greenway Path",
        "lat": 40.7033,
        "lon": -74.0170,
    },
    {
        "name": "Prospect Park West, Brooklyn, NY",
        "city": "Brooklyn, NY",
        "category": "Park Route",
        "lat": 40.6655,
        "lon": -73.9776,
    },
    {
        "name": "Market St at 4th St, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Downtown Hub",
        "lat": 37.7858,
        "lon": -122.4058,
    },
    {
        "name": "Golden Gate Park Panhandle, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Park Route",
        "lat": 37.7722,
        "lon": -122.4484,
    },
    {
        "name": "Ferry Building Embarcadero, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Waterfront Path",
        "lat": 37.7955,
        "lon": -122.3937,
    },
    {
        "name": "Seattle Waterfront / Pike Place, WA",
        "city": "Seattle, WA",
        "category": "Waterfront Path",
        "lat": 47.6085,
        "lon": -122.3406,
    },
    {
        "name": "Burke-Gilman Trail at UW, Seattle, WA",
        "city": "Seattle, WA",
        "category": "Greenway Path",
        "lat": 47.6512,
        "lon": -122.3075,
    },
    {
        "name": "Portland Waterfront Park, OR",
        "city": "Portland, OR",
        "category": "Waterfront Path",
        "lat": 45.5202,
        "lon": -122.6708,
    },
    {
        "name": "Tilikum Crossing, Portland, OR",
        "city": "Portland, OR",
        "category": "Bridge Bikeway",
        "lat": 45.5050,
        "lon": -122.6659,
    },
]

PRESET_LOCATIONS: Dict[str, Coordinate] = {
    location["name"]: Coordinate(location["lat"], location["lon"])
    for location in CYCLING_LOCATIONS
}

EXACT_LOCATION_INDEX: Dict[str, Tuple[Coordinate, str]] = {
    location["name"].lower(): (
        Coordinate(location["lat"], location["lon"]),
        location["name"],
    )
    for location in CYCLING_LOCATIONS
}


def search_location_suggestions(
    query: str, limit: int = 6
) -> List[Dict[str, str]]:
    """Return matching local cycling locations for instant autofill dropdown."""
    cleaned = (query or "").strip().lower()
    matches: List[Dict[str, str]] = []
    for location in CYCLING_LOCATIONS:
        name = str(location["name"])
        city = str(location["city"])
        category = str(location["category"])
        searchable = f"{name} {city} {category}".lower()
        if not cleaned or cleaned in searchable:
            matches.append(
                {"name": name, "city": city, "category": category}
            )
            if len(matches) >= max(1, limit):
                break
    return matches


def build_location_catalog_json() -> str:
    """Serialize curated locations with coordinates for browser autofill."""
    compact_entries = [
        {
            "name": str(loc["name"]),
            "city": str(loc["city"]),
            "category": str(loc["category"]),
            "lat": round(float(loc["lat"]), 6),
            "lon": round(float(loc["lon"]), 6),
        }
        for loc in CYCLING_LOCATIONS
    ]
    return json.dumps(compact_entries, separators=(",", ":"))


def fetch_json_url(url: str, timeout_secs: float = 3.5) -> Any:
    """Fetch and parse JSON from a URL via Pyodide or urllib.

    Note: Cannot be unit tested offline because it depends on live HTTP
    network access to remote OpenStreetMap/OSRM endpoints.
    """
    try:
        from pyodide.http import open_url  # type: ignore

        return json.loads(open_url(url).read())
    except ImportError:
        pass
    except Exception:
        return None

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SafeCycle-Drafter/2.0 (CS1 Bicycle Safety Planner)"
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_secs) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def parse_coordinate_pair(raw_text: str) -> Optional[Coordinate]:
    """Parse a 'lat, lon' coordinate pair if values are valid decimal degrees."""
    parts = [part.strip() for part in raw_text.split(",")]
    if len(parts) != 2:
        return None
    try:
        latitude = float(parts[0])
        longitude = float(parts[1])
    except ValueError:
        return None
    if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
        return Coordinate(latitude, longitude)
    return None


@functools.lru_cache(maxsize=64)
def fetch_nominatim_geocode(
    query: str,
) -> Optional[Tuple[float, float, str]]:
    """Query OpenStreetMap Nominatim (and Photon fallback) for custom addresses.

    Note: Cannot be unit tested offline because it depends on a live HTTP
    network call to nominatim.openstreetmap.org / photon.komoot.io.
    """
    encoded_query = urllib.parse.quote(query)
    photon_url = (
        f"https://photon.komoot.io/api/?q={encoded_query}"
        "&limit=1&lang=en&lat=39.68&lon=-75.75"
    )
    photon_data = fetch_json_url(photon_url, timeout_secs=3.0)
    if isinstance(photon_data, dict):
        features = photon_data.get("features") or []
        if features:
            feat = features[0]
            coords = (feat.get("geometry") or {}).get("coordinates") or []
            props = feat.get("properties") or {}
            if len(coords) >= 2:
                parts = [
                    str(props[k])
                    for k in ("name", "street", "city", "state")
                    if props.get(k)
                ]
                label = ", ".join(dict.fromkeys(parts)) if parts else query
                return (float(coords[1]), float(coords[0]), label)

    nom_url = (
        f"https://nominatim.openstreetmap.org/search?q={encoded_query}"
        "&format=json&limit=1"
    )
    payload = fetch_json_url(nom_url, timeout_secs=3.0)
    if isinstance(payload, list) and len(payload) > 0:
        first_match = payload[0]
        try:
            return (
                float(first_match["lat"]),
                float(first_match["lon"]),
                str(first_match.get("display_name", query)),
            )
        except (ValueError, KeyError, TypeError):
            pass
    return None


def geocode_address(
    address_text: str, allow_remote: bool = False
) -> Tuple[Optional[Coordinate], str]:
    """Resolve an address, catalog name, or 'lat, lon' into a Coordinate."""
    cleaned = (address_text or "").strip()
    if not cleaned:
        return (
            None,
            "Please enter a non-empty street address, landmark, or lat, lon.",
        )

    lowered = cleaned.lower()
    exact_hit = EXACT_LOCATION_INDEX.get(lowered)
    if exact_hit is not None:
        return exact_hit

    for key_lower, coord_pair in EXACT_LOCATION_INDEX.items():
        if lowered in key_lower or key_lower in lowered:
            return coord_pair

    parsed_coordinate = parse_coordinate_pair(cleaned)
    if parsed_coordinate is not None:
        formatted = (
            f"{parsed_coordinate.latitude:.4f}, "
            f"{parsed_coordinate.longitude:.4f}"
        )
        return (parsed_coordinate, formatted)

    if allow_remote:
        remote_result = fetch_nominatim_geocode(cleaned)
        if remote_result is not None:
            return (
                Coordinate(remote_result[0], remote_result[1]),
                remote_result[2],
            )

    return (
        None,
        f"Could not resolve '{cleaned}'. Pick a suggestion from the location "
        "autofill dropdown, enter a street address, or type coordinates like "
        "'39.6765, -75.7471'.",
    )
