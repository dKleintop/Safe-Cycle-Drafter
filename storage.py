"""
storage.py - Persistence for saved routes and GPX route export
Supports dual-mode storage: browser localStorage in Pyodide/Web, and JSON file/in-memory on server.
"""
import json
import os
import time
import io
from typing import List, Optional
from models import SavedRouteItem, RouteOption

LOCAL_STORAGE_KEY = "safecycle_saved_routes_v1"

BASE_DIR = "."
try:
    if "__file__" in globals() and globals().get("__file__"):
        BASE_DIR = os.path.dirname(os.path.abspath(globals()["__file__"]))
except Exception:
    BASE_DIR = "."
SAVED_ROUTES_FILE = os.path.join(BASE_DIR, "saved_routes.json") if BASE_DIR != "." else "saved_routes.json"

DEFAULT_SAVED_ROUTES = [
    {
        "route_id": "route_default_newark_kirkwood",
        "name": "Newark to Kirkwood Corridor",
        "start_label": "Louis Redding Hall, Newark, DE",
        "dest_label": "Kirkwood, DE",
        "route_type": "Balanced",
        "distance_km": 14.8,
        "duration_mins": 46.0,
        "safety_score": 82.0,
        "created_at": "2026-11-10 14:20",
        "gpx_content": """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SafeCycle GPS" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Newark to Kirkwood Corridor</name>
    <trkseg>
      <trkpt lat="39.6780" lon="-75.7505"><desc>Newark Start</desc></trkpt>
      <trkpt lat="39.6380" lon="-75.7480"><desc>DE 896 S Bike Shoulder</desc></trkpt>
      <trkpt lat="39.5850" lon="-75.7510"><desc>Kirkwood End</desc></trkpt>
    </trkseg>
  </trk>
</gpx>"""
    },
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
<gpx version="1.1" creator="SafeCycle GPS" xmlns="http://www.topografix.com/GPX/1/1">
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

def _get_js_storage():
    """Safely obtain browser localStorage object if running in Pyodide/Web environment."""
    try:
        import js
        if hasattr(js, "window") and hasattr(js.window, "localStorage"):
            return js.window.localStorage
    except Exception:
        pass
    return None

def load_saved_routes() -> List[SavedRouteItem]:
    """
    Load saved routes:
    1. Try browser localStorage (Pyodide web runtime).
    2. Fall back to in-memory cached routes.
    3. Fall back to saved_routes.json file on disk.
    4. Fall back to default corridor favorites.
    """
    global _IN_MEMORY_ROUTES

    # 1. Check browser localStorage
    storage = _get_js_storage()
    if storage is not None:
        try:
            raw = storage.getItem(LOCAL_STORAGE_KEY)
            if raw:
                items = json.loads(raw)
                if isinstance(items, list) and len(items) > 0:
                    _IN_MEMORY_ROUTES = [SavedRouteItem(**item) for item in items]
                    return list(_IN_MEMORY_ROUTES)
        except Exception:
            pass

    # 2. In-memory check
    if _IN_MEMORY_ROUTES:
        return list(_IN_MEMORY_ROUTES)

    # 3. Disk file check
    try:
        if os.path.exists(SAVED_ROUTES_FILE):
            with io.open(SAVED_ROUTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _IN_MEMORY_ROUTES = [SavedRouteItem(**item) for item in data]
                # Sync back to browser storage if available
                if storage is not None:
                    try:
                        storage.setItem(LOCAL_STORAGE_KEY, json.dumps(data))
                    except Exception:
                        pass
                return list(_IN_MEMORY_ROUTES)
    except Exception:
        pass

    # 4. Default routes
    _IN_MEMORY_ROUTES = [SavedRouteItem(**r) for r in DEFAULT_SAVED_ROUTES]
    save_all_routes(_IN_MEMORY_ROUTES)
    return list(_IN_MEMORY_ROUTES)

def save_all_routes(routes: List[SavedRouteItem]) -> None:
    """Serialize list of routes to browser localStorage, in-memory cache, and disk file."""
    global _IN_MEMORY_ROUTES
    _IN_MEMORY_ROUTES = list(routes)
    data = [r.__dict__ for r in routes]
    json_str = json.dumps(data, indent=2)

    # Browser localStorage
    storage = _get_js_storage()
    if storage is not None:
        try:
            storage.setItem(LOCAL_STORAGE_KEY, json_str)
        except Exception:
            pass

    # Local disk file fallback
    try:
        with io.open(SAVED_ROUTES_FILE, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception:
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
    """Add a new route to persistent storage and return the created item."""
    routes = load_saved_routes()
    new_id = f"route_{int(time.time() * 1000)}"
    timestamp = time.strftime("%Y-%m-%d %H:%M")
    clean_name = name.strip() or f"{start_label.split(',')[0]} to {dest_label.split(',')[0]} ({route_type})"
    
    # Check if duplicate already exists with exact same start, dest, and type
    for r in routes:
        if r.start_label.strip() == start_label.strip() and r.dest_label.strip() == dest_label.strip() and r.route_type == route_type:
            # Update name and timestamp
            r.name = clean_name
            r.created_at = timestamp
            r.distance_km = distance_km
            r.duration_mins = duration_mins
            r.safety_score = safety_score
            r.gpx_content = gpx_content
            save_all_routes(routes)
            return r

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

def is_route_saved(start_label: str, dest_label: str, route_type: str) -> bool:
    """Check if a route between start and dest with specific route type is already saved."""
    if not start_label or not dest_label:
        return False
    s1 = start_label.strip().lower()
    d1 = dest_label.strip().lower()
    for r in load_saved_routes():
        if r.start_label.strip().lower() == s1 and r.dest_label.strip().lower() == d1 and r.route_type.lower() == route_type.lower():
            return True
    return False

def get_saved_route_by_id(route_id: str) -> Optional[SavedRouteItem]:
    """Retrieve a single saved route item by route_id."""
    for r in load_saved_routes():
        if r.route_id == route_id:
            return r
    return None

def export_route_to_gpx(route: RouteOption, start_name: str, dest_name: str) -> str:
    """Generate valid GPX 1.1 XML string for external GPS units or bike computers."""
    points = []
    for seg in route.segments:
        for c in seg.coordinates:
            infra_desc = getattr(seg, 'infrastructure', 'road')
            points.append(f'      <trkpt lat="{c.latitude:.6f}" lon="{c.longitude:.6f}"><desc>{seg.name} ({infra_desc}, Safety: {seg.safety_score:.0f})</desc></trkpt>')
    
    pts_str = "\n".join(points)
    gpx = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SafeCycle — A Safety-First Bike GPS and Route Planner" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>{route.route_type} Bicycle Route: {start_name} to {dest_name}</name>
    <desc>Overall Safety Score: {route.overall_safety_score:.1f}/100 | Distance: {route.total_distance_km:.1f} km | Cycling Duration: {route.estimated_duration_mins:.0f} mins</desc>
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
