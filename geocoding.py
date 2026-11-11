"""
geocoding.py - Address resolution, geocoding, and rich cycling location autocomplete for SafeCycle
"""
import urllib.parse
import urllib.request
import urllib.error
import json
from typing import Optional, Tuple, Dict, List, Any
from models import Coordinate

# Comprehensive categorized bicycle destinations and landmarks
CYCLING_LOCATIONS: List[Dict[str, Any]] = [
    # Delaware Newark/Kirkwood Corridor (User route)
    {
        "name": "Louis Redding Hall, Newark, DE",
        "city": "Newark, DE",
        "category": "Campus Corridor",
        "icon": "🎓",
        "desc": "University of Delaware campus cycle corridor along S College Ave",
        "lat": 39.676456, "lon": -75.747050
    },
    {
        "name": "Kirkwood, DE",
        "city": "Kirkwood, DE",
        "category": "Trail Endpoint",
        "icon": "🎯",
        "desc": "Kirkwood community and C&D Canal trailhead connector",
        "lat": 39.571807, "lon": -75.696079
    },
    {
        "name": "University of Delaware, Newark, DE",
        "city": "Newark, DE",
        "category": "Campus Corridor",
        "icon": "🏫",
        "desc": "The Green and University of Delaware Newark cycling hub",
        "lat": 39.678044, "lon": -75.750668
    },
    {
        "name": "Lums Pond State Park, DE",
        "city": "Kirkwood, DE",
        "category": "Park Route",
        "icon": "🌲",
        "desc": "Scenic perimeter trail and cycling loops around Lums Pond",
        "lat": 39.559389, "lon": -75.719335
    },
    {
        "name": "Glasgow Park, Newark, DE",
        "city": "Newark, DE",
        "category": "Park Route",
        "icon": "🚲",
        "desc": "Dedicated multi-use paved cycling loop along Route 40 & Route 896",
        "lat": 39.610684, "lon": -75.729030
    },
    {
        "name": "Wilmington Riverfront, DE",
        "city": "Wilmington, DE",
        "category": "Greenway Path",
        "icon": "🌊",
        "desc": "Christina Riverfront bike path connecting to Jack A. Markell Trail",
        "lat": 39.734842, "lon": -75.556214
    },
    # New York City
    {
        "name": "Central Park South, New York, NY",
        "city": "New York, NY",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Gateway to Central Park scenic cycle drives and crosstown paths",
        "lat": 40.7661, "lon": -73.9772
    },
    {
        "name": "Brooklyn Bridge (Manhattan Side), NY",
        "city": "New York, NY",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "Dedicated two-way grade-separated cycle track over the East River",
        "lat": 40.7126, "lon": -74.0048
    },
    {
        "name": "Brooklyn Bridge (DUMBO / Brooklyn Side), NY",
        "city": "New York, NY",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "Access point to Brooklyn waterfront greenway and Brooklyn Bridge Park",
        "lat": 40.7028, "lon": -73.9928
    },
    {
        "name": "Hudson River Greenway at 72nd St, NY",
        "city": "New York, NY",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Premier off-street grade-separated waterfront bike highway",
        "lat": 40.7818, "lon": -73.9877
    },
    {
        "name": "Hudson River Greenway at Chelsea Piers (23rd St), NY",
        "city": "New York, NY",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Scenic waterfront path separated from motorized highway traffic",
        "lat": 40.7485, "lon": -74.0080
    },
    {
        "name": "Hudson River Greenway at Battery Park, NY",
        "city": "New York, NY",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Southern tip connection to East River Bikeway and Staten Island Ferry",
        "lat": 40.7033, "lon": -74.0170
    },
    {
        "name": "Prospect Park West, Brooklyn, NY",
        "city": "New York, NY",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Grand Army Plaza gateway and car-free Prospect Park interior loop",
        "lat": 40.6655, "lon": -73.9776
    },
    {
        "name": "Williamsburg Bridge Bike Path (Manhattan Ramp), NY",
        "city": "New York, NY",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "Dedicated grade-separated cycleway connecting Lower East Side & Brooklyn",
        "lat": 40.7183, "lon": -73.9872
    },
    {
        "name": "Manhattan Bridge Bikeway (Canal St), NY",
        "city": "New York, NY",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "North side protected bicycle lane into Downtown Brooklyn",
        "lat": 40.7155, "lon": -73.9945
    },
    {
        "name": "Times Square, New York, NY",
        "city": "New York, NY",
        "category": "City Landmark",
        "icon": "🏙️",
        "desc": "Broadway pedestrian plaza and shared cyclist avenue corridor",
        "lat": 40.7580, "lon": -73.9855
    },
    {
        "name": "Union Square South, New York, NY",
        "city": "New York, NY",
        "category": "City Landmark",
        "icon": "🏙️",
        "desc": "Major crosstown bicycle hub connecting Broadway and 14th St paths",
        "lat": 40.7359, "lon": -73.9911
    },
    {
        "name": "Washington Square Park, New York, NY",
        "city": "New York, NY",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Greenwich Village car-free park perimeter and 5th Ave starting point",
        "lat": 40.7308, "lon": -73.9973
    },
    {
        "name": "Grand Central Terminal, New York, NY",
        "city": "New York, NY",
        "category": "Transit Hub",
        "icon": "🚆",
        "desc": "Park Ave viaduct junction and East Midtown commuting nexus",
        "lat": 40.7527, "lon": -73.9772
    },
    {
        "name": "Penn Station / Moynihan Train Hall, NY",
        "city": "New York, NY",
        "category": "Transit Hub",
        "icon": "🚆",
        "desc": "Major transit terminal with 8th Ave and 9th Ave protected bike lanes",
        "lat": 40.7506, "lon": -73.9935
    },
    {
        "name": "Flushing Meadows Corona Park, Queens, NY",
        "city": "New York, NY",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Expansive paved greenway loops around Meadow Lake and Unisphere",
        "lat": 40.7498, "lon": -73.8465
    },

    # San Francisco & Bay Area
    {
        "name": "Market St at 4th St, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "City Landmark",
        "icon": "🏙️",
        "desc": "Car-free Better Market Street bicycle corridor and transit arterial",
        "lat": 37.7858, "lon": -122.4065
    },
    {
        "name": "Golden Gate Park Panhandle, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Tree-lined protected cycle boulevard leading into JFK Promenade",
        "lat": 37.7719, "lon": -122.4468
    },
    {
        "name": "The Embarcadero at Ferry Building, SF, CA",
        "city": "San Francisco, CA",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Wide waterfront promenade with separated bayside bike paths",
        "lat": 37.7955, "lon": -122.3937
    },
    {
        "name": "Golden Gate Bridge South Vista Point, SF, CA",
        "city": "San Francisco, CA",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "Iconic world-famous bicycle crossing into Marin County Headlands",
        "lat": 37.8078, "lon": -122.4751
    },
    {
        "name": "Valencia St Bikeway (16th St), San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Mission District center-running cycle track with bicycle signals",
        "lat": 37.7650, "lon": -122.4219
    },
    {
        "name": "Crissy Field Promenade, San Francisco, CA",
        "city": "San Francisco, CA",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Flat bayside multi-use path with sweeping bridge views",
        "lat": 37.8045, "lon": -122.4660
    },

    # Pacific Northwest & Western Hubs
    {
        "name": "Seattle Waterfront / Pike Place, WA",
        "city": "Seattle, WA",
        "category": "City Landmark",
        "icon": "🏙️",
        "desc": "New Alaskan Way protected bicycle pathway and Elliott Bay Trail",
        "lat": 47.6097, "lon": -122.3421
    },
    {
        "name": "Burke-Gilman Trail at UW, Seattle, WA",
        "city": "Seattle, WA",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "27-mile continuous multi-use rail-trail connecting northern Seattle",
        "lat": 47.6538, "lon": -122.3078
    },
    {
        "name": "Portland Waterfront Park, OR",
        "city": "Portland, OR",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Governor Tom McCall Waterfront Park and Willamette river loop",
        "lat": 45.5186, "lon": -122.6738
    },
    {
        "name": "Tilikum Crossing (Bridge of the People), Portland, OR",
        "city": "Portland, OR",
        "category": "Bridge Bikeway",
        "icon": "🌉",
        "desc": "Car-free cable-stayed bridge reserved exclusively for bikes, transit & walkers",
        "lat": 45.5053, "lon": -122.6663
    },

    # Chicago, Boston, DC, Austin
    {
        "name": "Chicago Lakefront Trail at Navy Pier, IL",
        "city": "Chicago, IL",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "18.5-mile grade-separated lakefront trail with dedicated bike lanes",
        "lat": 41.8917, "lon": -87.6086
    },
    {
        "name": "Charles River Esplanade, Boston, MA",
        "city": "Boston, MA",
        "category": "Park Route",
        "icon": "🌳",
        "desc": "Continuous river path connecting Boston and Cambridge without cross-traffic",
        "lat": 42.3554, "lon": -71.0776
    },
    {
        "name": "National Mall / Lincoln Memorial Bikeway, Washington, DC",
        "city": "Washington, DC",
        "category": "City Landmark",
        "icon": "🏙️",
        "desc": "Monumental wide cycleways connecting Capitol Hill and Potomac riverfront",
        "lat": 38.8893, "lon": -77.0502
    },
    {
        "name": "Mount Vernon Trail at Georgetown, Washington, DC",
        "city": "Washington, DC",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Paved scenic trail running south along the western bank of Potomac",
        "lat": 38.9036, "lon": -77.0673
    },
    {
        "name": "Lady Bird Lake Trail at Pfluger Bridge, Austin, TX",
        "city": "Austin, TX",
        "category": "Protected Greenway",
        "icon": "🚲",
        "desc": "Scenic Ann and Roy Butler Boardwalk and dedicated pedestrian/bike bridge",
        "lat": 30.2644, "lon": -97.7533
    }
]

# Preset locations dictionary for backward-compatibility with existing tests and modules
PRESET_LOCATIONS: Dict[str, Coordinate] = {
    loc["name"]: Coordinate(loc["lat"], loc["lon"]) for loc in CYCLING_LOCATIONS
}

def get_all_suggestions() -> List[Dict[str, Any]]:
    """Return all curated cycling suggestions."""
    return CYCLING_LOCATIONS

def get_suggestions_json() -> str:
    """Return JSON string of suggestions for frontend autocomplete dropdown."""
    return json.dumps(CYCLING_LOCATIONS)

def geocode_address(address_str: str) -> Tuple[Optional[Coordinate], str]:
    """
    Geocode an address string to Coordinate.
    Checks preset locations first, then queries OpenStreetMap Nominatim with proper headers.
    Returns (Coordinate, display_label_or_error_message).
    """
    clean_addr = address_str.strip()
    if not clean_addr:
        return (None, "Please enter a valid street address or location name.")

    # 1. Check presets (exact or title match first to avoid false positives)
    for loc in CYCLING_LOCATIONS:
        name = loc["name"]
        short_title = name.split(",")[0].strip()
        if clean_addr.lower() == name.lower() or clean_addr.lower() == short_title.lower():
            return (Coordinate(loc["lat"], loc["lon"]), name)

    # 2. Check if user passed direct "latitude, longitude"
    if "," in clean_addr:
        parts = clean_addr.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (Coordinate(lat, lon), f"GPS Coordinates: {lat:.4f}, {lon:.4f}")
            except ValueError:
                pass

    # 3. Expand US state abbreviations for worldwide geocoding disambiguation (e.g. DE -> Delaware)
    US_STATES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
        "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
        "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
    }
    search_query = clean_addr
    for abbr, full_state in US_STATES.items():
        if clean_addr.upper().endswith(f", {abbr}") or clean_addr.upper().endswith(f" {abbr}"):
            base = clean_addr[:-len(abbr)].strip().rstrip(",")
            search_query = f"{base}, {full_state}, USA"
            break

    # 4. Query Photon OpenStreetMap Geocoding (fast worldwide search)
    encoded_query = urllib.parse.quote(search_query)
    photon_url = f"https://photon.komoot.io/api/?q={encoded_query}&limit=1"
    try:
        data = None
        try:
            from pyodide.http import open_url
            with open_url(photon_url) as res:
                data = json.loads(res.read())
        except Exception:
            req = urllib.request.Request(photon_url, headers={"User-Agent": "SafeCycle-Bike-Planner/2.1 (contact: safety@safecycle.org)"})
            with urllib.request.urlopen(req, timeout=3.0) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode())
        if data:
            features = data.get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                p = features[0]["properties"]
                name = p.get("name") or p.get("street") or clean_addr
                city = p.get("city") or p.get("state") or p.get("country", "")
                short_disp = f"{name}, {city}" if city and city not in name else name
                return (Coordinate(float(coords[1]), float(coords[0])), short_disp)
    except Exception:
        pass

    # 4. Fallback to OpenStreetMap Nominatim (multi-stage query)
    nom_queries = [
        f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1&addressdetails=1&countrycodes=us",
        f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1&addressdetails=1",
        f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(clean_addr)}&format=json&limit=1&addressdetails=1"
    ]
    for n_url in nom_queries:
        try:
            data = None
            try:
                from pyodide.http import open_url
                with open_url(n_url) as res:
                    data = json.loads(res.read())
            except Exception:
                req = urllib.request.Request(n_url, headers={"User-Agent": "SafeCycle-Bike-Planner/2.1 (contact: safety@safecycle.org)"})
                with urllib.request.urlopen(req, timeout=3.5) as res:
                    if res.status == 200:
                        data = json.loads(res.read().decode())
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display = data[0].get("display_name", clean_addr)
                short_display = ", ".join(display.split(",")[:3])
                return (Coordinate(lat, lon), short_display)
        except Exception:
            pass

    # 5. Fuzzy preset match fallback (contains check or key tokens)
    clean_lower = clean_addr.lower()
    for loc in CYCLING_LOCATIONS:
        name_lower = loc["name"].lower()
        if clean_lower in name_lower or name_lower in clean_lower:
            return (Coordinate(loc["lat"], loc["lon"]), loc["name"])
        tokens = [t for t in clean_lower.replace(",", " ").split() if len(t) >= 4]
        if tokens and all(t in name_lower for t in tokens):
            return (Coordinate(loc["lat"], loc["lon"]), loc["name"])

    # 6. Default to first preset if location is completely unresolvable
    first_preset = CYCLING_LOCATIONS[0]
    return (Coordinate(first_preset["lat"], first_preset["lon"]), f"{clean_addr} (Estimated near {first_preset['name']})")
