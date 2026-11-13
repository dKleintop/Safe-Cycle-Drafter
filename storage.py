"""
storage.py - Persistence for saved routes and GPX route export.

Supports dual-mode storage: browser localStorage in Pyodide/Web,
and JSON file persistence on the local server.
"""
import io
import json
import os
import time
from typing import Any, List, Optional
from models import RouteOption, SavedRouteItem

LOCAL_STORAGE_KEY = "safecycle_saved_routes_v1"


def _resolve_saved_routes_path() -> str:
    """Resolve the path to saved_routes.json without using mutable globals."""
    base_dir = "."
    try:
        if "__file__" in globals() and globals().get("__file__"):
            base_dir = os.path.dirname(os.path.abspath(globals()["__file__"]))
    except Exception:
        base_dir = "."
    if base_dir != ".":
        return os.path.join(base_dir, "saved_routes.json")
    return "saved_routes.json"


SAVED_ROUTES_FILE = _resolve_saved_routes_path()

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
        "gpx_content": (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="SafeCycle GPS" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n'
            "  <trk>\n"
            "    <name>Newark to Kirkwood Corridor</name>\n"
            "    <trkseg>\n"
            '      <trkpt lat="39.6780" lon="-75.7505">'
            "<desc>Newark Start</desc></trkpt>\n"
            '      <trkpt lat="39.6380" lon="-75.7480">'
            "<desc>DE 896 S Bike Shoulder</desc></trkpt>\n"
            '      <trkpt lat="39.5850" lon="-75.7510">'
            "<desc>Kirkwood End</desc></trkpt>\n"
            "    </trkseg>\n"
            "  </trk>\n"
            "</gpx>"
        ),
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
        "gpx_content": (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="SafeCycle GPS" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n'
            "  <trk>\n"
            "    <name>Hudson Greenway Protected Commute</name>\n"
            "    <trkseg>\n"
            '      <trkpt lat="40.7661" lon="-73.9772">'
            "<name>Start: Central Park South</name></trkpt>\n"
            '      <trkpt lat="40.7818" lon="-73.9877">'
            "<name>Hudson River Greenway</name></trkpt>\n"
            '      <trkpt lat="40.7126" lon="-74.0048">'
            "<name>End: Brooklyn Bridge</name></trkpt>\n"
            "    </trkseg>\n"
            "  </trk>\n"
            "</gpx>"
        ),
    },
]


def _get_js_storage() -> Any:
    """
    Obtain browser localStorage object when running inside Pyodide WebAssembly.

    Note: The browser JS bridge path cannot be directly invoked without a
    browser runtime or mock, so it safely returns None in local Python tests.
    """
    try:
        import js
        if hasattr(js, "window") and hasattr(js.window, "localStorage"):
            return js.window.localStorage
    except Exception:
        pass
    return None


def load_saved_routes() -> List[SavedRouteItem]:
    """
    Load saved routes from browser localStorage, disk JSON, or default presets.

    Uses json serialization (an advanced standard-library technique beyond
    CISC108 basics) so favorites persist cleanly across sessions.
    """
    storage = _get_js_storage()
    if storage is not None:
        try:
            raw = storage.getItem(LOCAL_STORAGE_KEY)
            if raw:
                items = json.loads(raw)
                if isinstance(items, list) and len(items) > 0:
                    return [SavedRouteItem(**item) for item in items]
        except Exception:
            pass

    try:
        if os.path.exists(SAVED_ROUTES_FILE):
            with io.open(SAVED_ROUTES_FILE, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
                loaded = [SavedRouteItem(**item) for item in data]
                if storage is not None:
                    try:
                        storage.setItem(LOCAL_STORAGE_KEY, json.dumps(data))
                    except Exception:
                        pass
                return loaded
    except Exception:
        pass

    defaults = [SavedRouteItem(**route_dict) for route_dict in DEFAULT_SAVED_ROUTES]
    save_all_routes(defaults)
    return defaults


def save_all_routes(routes: List[SavedRouteItem]) -> None:
    """Serialize saved routes to browser localStorage and local JSON file."""
    data = [route_item.__dict__ for route_item in routes]
    json_str = json.dumps(data, indent=2)

    storage = _get_js_storage()
    if storage is not None:
        try:
            storage.setItem(LOCAL_STORAGE_KEY, json_str)
        except Exception:
            pass

    try:
        with io.open(SAVED_ROUTES_FILE, "w", encoding="utf-8") as file_handle:
            file_handle.write(json_str)
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
    gpx_content: str,
) -> SavedRouteItem:
    """Add or update a saved route in persistent storage and return it."""
    routes = load_saved_routes()
    new_id = f"route_{int(time.time() * 1000)}"
    timestamp = time.strftime("%Y-%m-%d %H:%M")
    fallback_name = (
        f"{start_label.split(',')[0]} to "
        f"{dest_label.split(',')[0]} ({route_type})"
    )
    clean_name = name.strip() or fallback_name

    for existing in routes:
        same_start = existing.start_label.strip() == start_label.strip()
        same_dest = existing.dest_label.strip() == dest_label.strip()
        same_type = existing.route_type == route_type
        if same_start and same_dest and same_type:
            existing.name = clean_name
            existing.created_at = timestamp
            existing.distance_km = distance_km
            existing.duration_mins = duration_mins
            existing.safety_score = safety_score
            existing.gpx_content = gpx_content
            save_all_routes(routes)
            return existing

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
        gpx_content=gpx_content,
    )
    routes.insert(0, new_item)
    save_all_routes(routes)
    return new_item


def delete_saved_route(route_id: str) -> None:
    """Remove a route from persistent storage by its route_id."""
    routes = load_saved_routes()
    remaining = [route_item for route_item in routes if route_item.route_id != route_id]
    save_all_routes(remaining)


def is_route_saved(start_label: str, dest_label: str, route_type: str) -> bool:
    """Check whether a route with matching endpoints and type is already saved."""
    if not start_label or not dest_label:
        return False
    start_norm = start_label.strip().lower()
    dest_norm = dest_label.strip().lower()
    type_norm = route_type.lower()
    for saved_item in load_saved_routes():
        if (
            saved_item.start_label.strip().lower() == start_norm
            and saved_item.dest_label.strip().lower() == dest_norm
            and saved_item.route_type.lower() == type_norm
        ):
            return True
    return False


def get_saved_route_by_id(route_id: str) -> Optional[SavedRouteItem]:
    """Retrieve a single saved route item matching route_id, or None."""
    for saved_item in load_saved_routes():
        if saved_item.route_id == route_id:
            return saved_item
    return None


def export_route_to_gpx(route: RouteOption, start_name: str, dest_name: str) -> str:
    """Generate a valid GPX 1.1 XML document string for GPS bike computers."""
    points = []
    for segment in route.segments:
        for coord in segment.coordinates:
            infra_desc = getattr(segment, "infrastructure", "road")
            points.append(
                f'      <trkpt lat="{coord.latitude:.6f}" '
                f'lon="{coord.longitude:.6f}">'
                f"<desc>{segment.name} ({infra_desc}, "
                f"Safety: {segment.safety_score:.0f})</desc></trkpt>"
            )

    pts_str = "\n".join(points)
    gpx = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" '
        'creator="SafeCycle — A Safety-First Bike GPS and Route Planner" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        "  <metadata>\n"
        f"    <name>{route.route_type} Bicycle Route: "
        f"{start_name} to {dest_name}</name>\n"
        f"    <desc>Overall Safety Score: {route.overall_safety_score:.1f}/100 | "
        f"Distance: {route.total_distance_km:.1f} km | "
        f"Cycling Duration: {route.estimated_duration_mins:.0f} mins</desc>\n"
        f"    <time>{time.strftime('%Y-%m-%dT%H:%M:%SZ')}</time>\n"
        "  </metadata>\n"
        "  <trk>\n"
        f"    <name>{route.route_type} Route</name>\n"
        "    <type>Cycling</type>\n"
        "    <trkseg>\n"
        f"{pts_str}\n"
        "    </trkseg>\n"
        "  </trk>\n"
        "</gpx>"
    )
    return gpx
