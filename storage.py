"""
storage.py - Persistence for saved routes and GPX route export
"""
import json
import os
import time
from typing import List, Optional
from models import SavedRouteItem, RouteOption

import io

BASE_DIR = "."
try:
    if "__file__" in globals() and globals().get("__file__"):
        BASE_DIR = os.path.dirname(os.path.abspath(globals()["__file__"]))
except Exception:
    BASE_DIR = "."
SAVED_ROUTES_FILE = os.path.join(BASE_DIR, "saved_routes.json") if BASE_DIR != "." else "saved_routes.json"

DEFAULT_SAVED_ROUTES = [
    {
        "route_id": "route_default_1",
        "name": "Hudson Greenway Protected Commute",
        "start_label": "Central Park South, New York, NY",
        "dest_label": "Brooklyn Bridge (Manhattan Side), NY",
        "route_type": "Safest",
        "distance_km": 8.6,
        "duration_mins": 29.5,
        "safety_score": 88.5,
        "created_at": "2026-10-18 08:30",
        "gpx_content": """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SafeCycle GPS">
  <trk>
    <name>Hudson Greenway Protected Commute</name>
    <trkseg>
      <trkpt lat="40.7661" lon="-73.9772"><name>Start: Central Park South</name></trkpt>
      <trkpt lat="40.7818" lon="-73.9877"><name>Hudson River Greenway</name></trkpt>
      <trkpt lat="40.7126" lon="-74.0048"><name>End: Brooklyn Bridge</name></trkpt>
    </trkseg>
  </trk>
</gpx>"""
    }
]

_IN_MEMORY_ROUTES: List[SavedRouteItem] = []

def load_saved_routes() -> List[SavedRouteItem]:
    """Load saved routes from JSON storage file, or in-memory fallback, or return defaults."""
    global _IN_MEMORY_ROUTES
    if _IN_MEMORY_ROUTES:
        return list(_IN_MEMORY_ROUTES)

    try:
        if os.path.exists(SAVED_ROUTES_FILE):
            with io.open(SAVED_ROUTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _IN_MEMORY_ROUTES = [SavedRouteItem(**item) for item in data]
                return list(_IN_MEMORY_ROUTES)
    except Exception:
        pass

    _IN_MEMORY_ROUTES = [SavedRouteItem(**r) for r in DEFAULT_SAVED_ROUTES]
    save_all_routes(_IN_MEMORY_ROUTES)
    return list(_IN_MEMORY_ROUTES)

def save_all_routes(routes: List[SavedRouteItem]) -> None:
    """Serialize list of routes to disk and in-memory cache."""
    global _IN_MEMORY_ROUTES
    _IN_MEMORY_ROUTES = list(routes)
    try:
        data = [r.__dict__ for r in routes]
        with io.open(SAVED_ROUTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        # Filesystem write might be restricted in browser Pyodide runtime; in-memory cache holds state
        pass

def add_saved_route(
    name: str,
    start_label: str,
    dest_label: str,
    route_type: str,
    distance_km: float,
    duration_mins: float,
    safety_score: float,
    gpx_content: str
) -> SavedRouteItem:
    """Add a new route to persistent storage."""
    routes = load_saved_routes()
    new_id = f"route_{int(time.time() * 1000)}"
    timestamp = time.strftime("%Y-%m-%d %H:%M")
    clean_name = name.strip() or f"{start_label.split(',')[0]} to {dest_label.split(',')[0]}"
    
    new_item = SavedRouteItem(
        route_id=new_id,
        name=clean_name,
        start_label=start_label,
        dest_label=dest_label,
        route_type=route_type,
        distance_km=distance_km,
        duration_mins=duration_mins,
        safety_score=safety_score,
        created_at=timestamp,
        gpx_content=gpx_content
    )
    routes.insert(0, new_item)
    save_all_routes(routes)
    return new_item

def delete_saved_route(route_id: str) -> None:
    """Remove a route from persistent storage by ID."""
    routes = load_saved_routes()
    routes = [r for r in routes if r.route_id != route_id]
    save_all_routes(routes)

def export_route_to_gpx(route: RouteOption, start_name: str, dest_name: str) -> str:
    """Generate valid GPX 1.1 XML string for external GPS units or bike computers."""
    points = []
    for seg in route.segments:
        for c in seg.coordinates:
            points.append(f'      <trkpt lat="{c.latitude:.6f}" lon="{c.longitude:.6f}"><desc>{seg.name} (Safety Score: {seg.safety_score})</desc></trkpt>')
    
    pts_str = "\n".join(points)
    gpx = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SafeCycle — A Safety-First Bike GPS and Route Planner" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>{route.route_type} Bicycle Route: {start_name} to {dest_name}</name>
    <desc>Overall Safety Score: {route.overall_safety_score}/100 | Distance: {route.total_distance_km:.1f} km | Cycling Duration: {route.estimated_duration_mins:.0f} mins</desc>
    <time>{time.strftime('%Y-%m-%dT%H:%M:%SZ')}</time>
  </metadata>
  <trk>
    <name>{route.route_type} Route</name>
    <type>Cycling</type>
    <trkseg>
{pts_str}
    </trkseg>
  </trk>
</gpx>"""
    return gpx
