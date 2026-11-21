"""routing.py - Real street-following bicycle routing, Dijkstra graph & timing.

Advanced technique notes (beyond introductory CS1):
- Queries OpenStreetMap's public FOSSGIS OSRM bicycle and vehicle routing APIs
  (`routing.openstreetmap.de/routed-bike` and `routed-car`) with
  `functools.lru_cache` memoization to build real street-following bike routes
  with actual road geometry and street names, falling back seamlessly to an
  offline safety-weighted Dijkstra graph when offline or running unit tests.
- Uses `heapq` (binary min-heap priority queue) to implement Dijkstra's
  shortest-path algorithm over a weighted cycling road network graph.
- Uses `math` trigonometric functions (`sin`, `cos`, `atan2`, `sqrt`, `hypot`)
  for Haversine great-circle distance and alternate corridor via-waypoints.
- Uses `datetime` and `timedelta` to calculate formatted departure and arrival
  clock schedules from 24-hour HH:MM input strings.
"""

import functools
import heapq
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from geocoding import fetch_json_url
from models import (
    Coordinate,
    CrashRecord,
    RoadSegment,
    RouteOption,
)
from safety import evaluate_road_safety

EARTH_RADIUS_KM: float = 6371.0
MILES_PER_KM: float = 0.621371
KM_PER_MILE: float = 1.60934
NEWARK_ANCHOR: Coordinate = Coordinate(39.676456, -75.747050)
KIRKWOOD_ANCHOR: Coordinate = Coordinate(39.571807, -75.696079)

DEDICATED_BIKE_FACILITIES: Tuple[str, ...] = (
    "protected_bike_path",
    "separated_lane",
    "painted_lane",
    "paved_shoulder",
    "traffic_calmed_street",
)

MOTORWAY_KEYWORDS: Tuple[str, ...] = (
    "interstate",
    "expressway",
    "freeway",
    "turnpike",
    "i-",
    "i 95",
    "i 495",
    "i 295",
)

MAJOR_HIGHWAY_KEYWORDS: Tuple[str, ...] = (
    "highway",
    "hwy",
    "pike",
    "bypass",
    "thruway",
    "us ",
    "us-",
)

STATE_ROUTE_KEYWORDS: Tuple[str, ...] = (
    "route ",
    "rt ",
    "de ",
    "de-",
    "md ",
    "md-",
    "pa ",
    "pa-",
    "nj ",
    "nj-",
    "sr ",
    "boulevard",
    "blvd",
    "parkway",
    "pkwy",
)

TRAIL_KEYWORDS: Tuple[str, ...] = (
    "trail",
    "greenway",
    "path",
    "cycleway",
    "bikeway",
    "towpath",
    "boardwalk",
    "promenade",
    "canal",
    "riverwalk",
    "esplanade",
)

QUIET_STREET_KEYWORDS: Tuple[str, ...] = (
    "lane",
    "ln",
    "court",
    "ct",
    "circle",
    "cir",
    "place",
    "pl",
    "terrace",
    "ter",
    "way",
    "campus",
    "alley",
    "driveway",
    "walk",
    "drive",
    "dr",
    "close",
    "loop",
    "commons",
    "green",
)


def calculate_haversine_distance_km(
    origin: Coordinate, destination: Coordinate
) -> float:
    """Compute great-circle distance in kilometers between two Coordinates."""
    origin_lat = math.radians(origin.latitude)
    dest_lat = math.radians(destination.latitude)
    delta_lat = math.radians(destination.latitude - origin.latitude)
    delta_lon = math.radians(destination.longitude - origin.longitude)
    haversine_term = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(origin_lat)
        * math.cos(dest_lat)
        * math.sin(delta_lon / 2.0) ** 2
    )
    central_angle = 2.0 * math.atan2(
        math.sqrt(haversine_term),
        math.sqrt(max(0.0, 1.0 - haversine_term)),
    )
    return EARTH_RADIUS_KM * central_angle


def parse_speed_mph(raw_value: Any, default_speed: float = 12.0) -> float:
    """Parse planned cycling speed (mph), clamped to 5.0-28.0 mph."""
    try:
        parsed_speed = float(str(raw_value).strip())
    except (ValueError, TypeError):
        return default_speed
    if math.isnan(parsed_speed) or math.isinf(parsed_speed):
        return default_speed
    return round(max(5.0, min(28.0, parsed_speed)), 1)


def parse_detour_ratio(detour_label: str) -> float:
    """Convert a detour tolerance label ('15%', '50%') into a ratio."""
    cleaned_text = (detour_label or "50%").replace("%", "").strip()
    try:
        percent_value = float(cleaned_text)
    except ValueError:
        percent_value = 50.0
    return 1.0 + max(0.05, min(1.5, percent_value / 100.0))


def get_time_of_day_traffic_note(start_time_24h: str) -> Tuple[str, float]:
    """Return a traffic exposure advisory and multiplier for departure time."""
    departure_hour = 8
    try:
        time_parts = (start_time_24h or "08:30").strip().split(":")
        departure_hour = int(time_parts[0]) % 24
    except (ValueError, IndexError):
        departure_hour = 8

    if 7 <= departure_hour <= 9:
        return (
            "Morning commute peak: elevated intersection turning volume.",
            1.15,
        )
    if 16 <= departure_hour <= 18:
        return (
            "Evening rush hour: heavier arterial traffic and lower visibility.",
            1.20,
        )
    if departure_hour >= 20 or departure_hour < 6:
        return (
            "Night / low-light riding: lights and reflective gear advised.",
            1.18,
        )
    return ("Off-peak daytime traffic: typical motor vehicle exposure.", 1.0)


def compute_trip_schedule(
    start_time_24h: str, duration_mins: float
) -> Tuple[str, str]:
    """Format departure and arrival clock times from a 24-hour HH:MM string."""
    try:
        cleaned_time = (start_time_24h or "08:30").strip()[:5]
        depart_dt = datetime.strptime(cleaned_time, "%H:%M")
    except ValueError:
        depart_dt = datetime.strptime("08:30", "%H:%M")
    arrive_dt = depart_dt + timedelta(minutes=max(1.0, duration_mins))
    depart_text = depart_dt.strftime("%I:%M %p").lstrip("0")
    arrive_text = arrive_dt.strftime("%I:%M %p").lstrip("0")
    return (depart_text, arrive_text)


def format_duration_text(duration_mins: float) -> str:
    """Format cycling minutes into readable '42 min' or '1 hr 12 min'."""
    total_minutes = max(1, int(round(duration_mins)))
    if total_minutes < 60:
        return f"{total_minutes} min"
    hours = total_minutes // 60
    remaining_minutes = total_minutes % 60
    if remaining_minutes == 0:
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    return f"{hours} hr {remaining_minutes} min"


def format_distance(distance_km: float, units: str = "mi") -> str:
    """Format distance consistently in miles or kilometers."""
    if units == "km":
        return f"{distance_km:.1f} km"
    miles = distance_km * MILES_PER_KM
    return f"{miles:.1f} mi"


def make_evaluated_segment(
    segment_id: str,
    name: str,
    coordinates: List[Coordinate],
    length_km: float,
    infrastructure: str,
    speed_limit_mph: Optional[int],
    traffic_exposure: str,
    crash_record: Optional[CrashRecord],
    intersection_risk: str,
    safer_alternative: str = "",
) -> RoadSegment:
    """Create a RoadSegment and immediately evaluate its safety score."""
    score, category, confidence, positives, negatives, notes = (
        evaluate_road_safety(
            infrastructure=infrastructure,
            speed_limit_mph=speed_limit_mph,
            traffic_exposure=traffic_exposure,
            crash_record=crash_record,
            intersection_risk=intersection_risk,
        )
    )
    return RoadSegment(
        segment_id=segment_id,
        name=name,
        coordinates=coordinates,
        length_km=round(max(0.05, length_km), 2),
        infrastructure=infrastructure,
        speed_limit_mph=speed_limit_mph,
        traffic_exposure=traffic_exposure,
        crash_record=crash_record,
        intersection_risk=intersection_risk,
        safety_score=score,
        confidence=confidence,
        risk_category=category,
        positive_factors=positives,
        negative_factors=negatives,
        evidence_notes=notes,
        safer_alternative=safer_alternative,
    )


def downsample_coordinates(
    coords: List[Coordinate], max_points: int = 28
) -> List[Coordinate]:
    """Keep first, last, and evenly spaced points so polylines stay crisp."""
    if len(coords) <= max_points or max_points < 2:
        return list(coords)
    step = (len(coords) - 1) / float(max_points - 1)
    sampled = [coords[int(round(i * step))] for i in range(max_points - 1)]
    sampled.append(coords[-1])
    return sampled


def normalize_street_key(street_name: str) -> str:
    """Normalize a street name for overlap and backtrack comparisons."""
    base = (street_name or "").split("(")[0].strip().lower()
    if base in ("bikeway / path connector", "connecting roadway", ""):
        return ""
    return " ".join(base.split())


def contains_any_word_phrase(
    text: str, phrases: Tuple[str, ...]
) -> bool:
    """Match road-type keywords on word boundaries to avoid substring bugs."""
    cleaned = re.sub(r"[^a-z0-9\-]+", " ", (text or "").lower()).strip()
    if not cleaned:
        return False
    padded = f" {cleaned} "
    for phrase in phrases:
        if phrase.endswith("-"):
            if f" {phrase}" in padded:
                return True
        elif phrase.endswith(" "):
            if f" {phrase}" in padded:
                return True
        else:
            if f" {phrase} " in padded:
                return True
    return False


def infer_osm_segment_attributes(
    street_name: str,
    mode_name: str,
    road_classes: Tuple[str, ...] = (),
) -> Tuple[str, Optional[int], str, str, str]:
    """Infer cycling safety attributes objectively from OpenStreetMap tags.

    Scoring depends strictly on road classification, highway ref, travel mode,
    and intersection classes so identical streets always receive the exact same
    safety score regardless of which route uses them.
    """
    lowered_name = (street_name or "").lower().strip()
    lowered_mode = (mode_name or "").lower().strip()
    lowered_classes = {str(cls).lower() for cls in road_classes}

    if (
        "motorway" in lowered_classes
        or "toll" in lowered_classes
        or contains_any_word_phrase(lowered_name, MOTORWAY_KEYWORDS)
    ):
        return (
            "none",
            55,
            "heavy",
            "high_conflict",
            "Avoid limited-access highways; use a parallel local corridor.",
        )

    if contains_any_word_phrase(lowered_name, MAJOR_HIGHWAY_KEYWORDS):
        return (
            "none",
            45,
            "heavy",
            "high_conflict",
            "Switch to a quieter parallel road or greenway to avoid highway traffic.",
        )

    if contains_any_word_phrase(lowered_name, STATE_ROUTE_KEYWORDS):
        return (
            "shared_lane",
            35,
            "high",
            "moderate",
            "Watch for faster motor traffic and turning lanes on this state route.",
        )

    if contains_any_word_phrase(lowered_name, TRAIL_KEYWORDS):
        return ("protected_bike_path", 15, "very_low", "low", "")

    if lowered_mode in ("pushing bike", "ferry") or "foot" in lowered_mode:
        return ("separated_lane", 15, "very_low", "low", "")

    if lowered_name == "bikeway / path connector":
        return ("separated_lane", 15, "very_low", "low", "")

    if lowered_name == "connecting roadway":
        return (
            "shared_lane",
            30,
            "moderate",
            "moderate",
            "Verify shoulder width and crossing visibility on this connector.",
        )

    if contains_any_word_phrase(lowered_name, QUIET_STREET_KEYWORDS):
        return ("traffic_calmed_street", 20, "low", "low", "")

    return ("shared_lane", 25, "low", "low", "")


def build_segments_from_osrm_route(
    osrm_route: Dict[str, Any], prefix: str
) -> List[RoadSegment]:
    """Convert an OSRM GeoJSON route with steps into scored RoadSegments."""
    legs = osrm_route.get("legs") or []
    grouped: List[Dict[str, Any]] = []

    for leg in legs:
        for step in leg.get("steps") or []:
            dist_m = float(step.get("distance") or 0.0)
            geom = (step.get("geometry") or {}).get("coordinates") or []
            if len(geom) < 2 and dist_m < 10.0:
                continue
            step_coords = [
                Coordinate(round(float(pt[1]), 6), round(float(pt[0]), 6))
                for pt in geom
                if len(pt) >= 2
            ]
            if not step_coords:
                continue
            raw_name = str(step.get("name") or "").strip()
            ref_name = str(step.get("ref") or "").strip()
            mode_name = str(step.get("mode") or "cycling")
            step_classes = set()
            for inter in step.get("intersections") or []:
                for cls_name in inter.get("classes") or []:
                    step_classes.add(str(cls_name).lower())

            if raw_name and ref_name and ref_name not in raw_name:
                display_name = f"{raw_name} ({ref_name})"
            elif raw_name:
                display_name = raw_name
            elif ref_name:
                display_name = ref_name
            elif "driving" in mode_name.lower():
                display_name = "Connecting Roadway"
            else:
                display_name = "Bikeway / Path Connector"

            if grouped and (
                grouped[-1]["name"] == display_name
                or (dist_m < 140.0 and raw_name == "" and ref_name == "")
            ):
                grouped[-1]["dist_m"] += dist_m
                grouped[-1]["coords"].extend(step_coords[1:])
                grouped[-1]["classes"].update(step_classes)
            else:
                grouped.append(
                    {
                        "name": display_name,
                        "mode": mode_name,
                        "dist_m": dist_m,
                        "coords": step_coords,
                        "classes": step_classes,
                    }
                )

    merged: List[Dict[str, Any]] = []
    for entry in grouped:
        if (
            merged
            and len(grouped) > 10
            and entry["dist_m"] < 220.0
            and len(merged) >= 1
        ):
            merged[-1]["dist_m"] += entry["dist_m"]
            merged[-1]["coords"].extend(entry["coords"][1:])
            merged[-1]["classes"].update(entry["classes"])
        else:
            merged.append(entry)

    segments: List[RoadSegment] = []
    for index, item in enumerate(merged, start=1):
        road_classes = tuple(sorted(item["classes"]))
        infra, speed_mph, traffic, inter_risk, alt_tip = (
            infer_osm_segment_attributes(
                item["name"], item["mode"], road_classes
            )
        )
        crash_record: Optional[CrashRecord] = None
        if infra in ("protected_bike_path", "separated_lane"):
            crash_record = CrashRecord(0, 0, 0, "OSM Bikeway Baseline")
        elif infra == "none" and (speed_mph or 0) >= 45:
            crash_record = CrashRecord(3, 1, 0, "Regional Arterial Estimate")

        segments.append(
            make_evaluated_segment(
                segment_id=f"{prefix}_{index}",
                name=item["name"],
                coordinates=downsample_coordinates(item["coords"], 28),
                length_km=max(0.08, item["dist_m"] / 1000.0),
                infrastructure=infra,
                speed_limit_mph=speed_mph,
                traffic_exposure=traffic,
                crash_record=crash_record,
                intersection_risk=inter_risk,
                safer_alternative=alt_tip,
            )
        )
    return segments


def compute_via_waypoint(
    origin: Coordinate, destination: Coordinate, offset_fraction: float
) -> Coordinate:
    """Compute a perpendicular midpoint waypoint for alternate road routing."""
    mid_lat = (origin.latitude + destination.latitude) / 2.0
    mid_lon = (origin.longitude + destination.longitude) / 2.0
    delta_lat = destination.latitude - origin.latitude
    delta_lon = destination.longitude - origin.longitude
    span = math.hypot(delta_lat, delta_lon) or 0.002
    perp_lat = -delta_lon / span
    perp_lon = delta_lat / span
    offset_deg = max(0.004, min(0.025, span * abs(offset_fraction)))
    sign = 1.0 if offset_fraction >= 0.0 else -1.0
    return Coordinate(
        round(mid_lat + sign * perp_lat * offset_deg, 5),
        round(mid_lon + sign * perp_lon * offset_deg, 5),
    )


def score_segments_weighted(segments: List[RoadSegment]) -> float:
    """Return length-weighted mean safety score for a list of RoadSegments."""
    total_km = sum(segment.length_km for segment in segments)
    if total_km <= 0.0:
        return 0.0
    return (
        sum(segment.safety_score * segment.length_km for segment in segments)
        / total_km
    )


def has_backtrack_loop(segments: List[RoadSegment]) -> bool:
    """Return True if a route contains a tight out-and-back cul-de-sac spur."""
    entries: List[Tuple[str, float]] = []
    for seg in segments:
        key = normalize_street_key(seg.name)
        if entries and key and entries[-1][0] == key:
            prev_key, prev_km = entries[-1]
            entries[-1] = (prev_key, prev_km + seg.length_km)
        else:
            entries.append((key, seg.length_km))

    for idx, (street_key, _) in enumerate(entries):
        if not street_key:
            continue
        between_km = 0.0
        for next_idx in range(idx + 1, min(len(entries), idx + 4)):
            next_key, next_km = entries[next_idx]
            if next_key == street_key:
                if between_km <= 1.4:
                    return True
                break
            between_km += next_km
    return False


def flatten_route_coords(segments: List[RoadSegment]) -> List[Coordinate]:
    """Flatten segment coordinate lists into a single continuous path."""
    coords: List[Coordinate] = []
    for seg in segments:
        for coord in seg.coordinates:
            if not coords or (
                coords[-1].latitude != coord.latitude
                or coords[-1].longitude != coord.longitude
            ):
                coords.append(coord)
    return coords


def compute_route_overlap_ratio(
    segs_a: List[RoadSegment], segs_b: List[RoadSegment]
) -> float:
    """Return length-weighted shared-street ratio (0.0 to 1.0) of two routes."""
    lengths_a: Dict[str, float] = {}
    lengths_b: Dict[str, float] = {}
    for seg in segs_a:
        key = normalize_street_key(seg.name)
        if key:
            lengths_a[key] = lengths_a.get(key, 0.0) + seg.length_km
    for seg in segs_b:
        key = normalize_street_key(seg.name)
        if key:
            lengths_b[key] = lengths_b.get(key, 0.0) + seg.length_km

    total_a = sum(lengths_a.values())
    total_b = sum(lengths_b.values())
    denom = min(total_a, total_b)
    if denom <= 0.05:
        return 0.0
    shared = sum(
        min(lengths_a[key], lengths_b[key])
        for key in lengths_a
        if key in lengths_b
    )
    return min(1.0, shared / denom)


def compute_corridor_separation_km(
    segs_a: List[RoadSegment], segs_b: List[RoadSegment]
) -> float:
    """Return mean interior distance (km) separating two candidate routes."""
    pts_a = downsample_coordinates(flatten_route_coords(segs_a), 14)
    pts_b = downsample_coordinates(flatten_route_coords(segs_b), 14)
    if len(pts_a) < 3 or len(pts_b) < 3:
        return 0.0
    interior_a = pts_a[1:-1]
    separations: List[float] = []
    for pt_a in interior_a:
        min_dist = min(
            calculate_haversine_distance_km(pt_a, pt_b) for pt_b in pts_b
        )
        separations.append(min_dist)
    return sum(separations) / float(len(separations))


def are_routes_similar(
    segs_a: List[RoadSegment],
    segs_b: List[RoadSegment],
    straight_km: float = 1.0,
) -> bool:
    """Return True if two routes trace effectively the same physical path."""
    overlap = compute_route_overlap_ratio(segs_a, segs_b)
    if overlap >= 0.72:
        return True
    sep_km = compute_corridor_separation_km(segs_a, segs_b)
    threshold_km = max(0.12, min(0.65, straight_km * 0.035))
    return sep_km < threshold_km


def retag_route_segments(
    segments: List[RoadSegment], prefix: str
) -> List[RoadSegment]:
    """Return a copy of segments with unique IDs prefixed by route mode."""
    retagged: List[RoadSegment] = []
    for idx, seg in enumerate(segments, start=1):
        retagged.append(
            RoadSegment(
                segment_id=f"{prefix}_{idx}",
                name=seg.name,
                coordinates=list(seg.coordinates),
                length_km=seg.length_km,
                infrastructure=seg.infrastructure,
                speed_limit_mph=seg.speed_limit_mph,
                traffic_exposure=seg.traffic_exposure,
                crash_record=seg.crash_record,
                intersection_risk=seg.intersection_risk,
                safety_score=seg.safety_score,
                confidence=seg.confidence,
                risk_category=seg.risk_category,
                positive_factors=list(seg.positive_factors),
                negative_factors=list(seg.negative_factors),
                evidence_notes=seg.evidence_notes,
                safer_alternative=seg.safer_alternative,
            )
        )
    return retagged


def select_distinct_ranked_routes(
    candidates: List[Tuple[List[RoadSegment], str]],
    planned_speed_mph: float,
    start_time_24h: str,
    detour_tolerance: str,
    straight_km: float,
) -> Dict[str, RouteOption]:
    """Deduplicate candidate corridors and return up to top 3 distinct routes.

    Returns 1, 2, or 3 genuinely distinct routes labeled Safest, Balanced, and
    Direct based on objective safety score and total distance.
    """
    valid: List[Tuple[float, float, List[RoadSegment], str]] = []
    for segs, source_label in candidates:
        if not segs or has_backtrack_loop(segs):
            continue
        dist_km = sum(seg.length_km for seg in segs)
        if dist_km <= 0.05:
            continue
        score = round(score_segments_weighted(segs), 1)
        valid.append((score, dist_km, segs, source_label))

    if not valid:
        return {}

    shortest_km = min(item[1] for item in valid)
    max_detour = max(1.65, parse_detour_ratio(detour_tolerance) + 0.15)
    pruned = [
        item for item in valid if item[1] <= shortest_km * max_detour
    ] or [min(valid, key=lambda item: item[1])]

    # Deduplicate overlapping corridors, preferring bike-routed & higher-scored
    pruned.sort(
        key=lambda item: (
            0 if "Bicycle" in item[3] else 1,
            -item[0],
            item[1],
        )
    )
    unique: List[Tuple[float, float, List[RoadSegment], str]] = []
    for item in pruned:
        duplicate_idx = -1
        for idx, existing in enumerate(unique):
            if are_routes_similar(item[2], existing[2], straight_km):
                duplicate_idx = idx
                break
        if duplicate_idx == -1:
            unique.append(item)
        else:
            existing = unique[duplicate_idx]
            same_tier = ("Bicycle" in item[3]) == ("Bicycle" in existing[3])
            if (
                same_tier
                and item[1] < existing[1]
                and item[0] >= existing[0] - 0.5
            ):
                unique[duplicate_idx] = item

    safest_item = max(unique, key=lambda item: (item[0], -item[1]))
    remaining = [item for item in unique if item is not safest_item]

    result: Dict[str, RouteOption] = {
        "Safest": package_route_option(
            "Safest",
            retag_route_segments(safest_item[2], "osm_safe"),
            planned_speed_mph,
            start_time_24h,
            (
                "Highest-scoring distinct corridor based on objective road "
                "class, bike facilities, and motor-vehicle speed exposure."
            ),
            elevation_gain_m=14.0 + straight_km * 2.1,
            routing_source=safest_item[3],
        )
    }

    if not remaining:
        return result

    direct_item = min(remaining, key=lambda item: (item[1], -item[0]))
    middle_pool = [item for item in remaining if item is not direct_item]

    if middle_pool:
        balanced_item = max(
            middle_pool,
            key=lambda item: item[0] - (item[1] / max(0.5, shortest_km)) * 6.0,
        )
        result["Balanced"] = package_route_option(
            "Balanced",
            retag_route_segments(balanced_item[2], "osm_bal"),
            planned_speed_mph,
            start_time_24h,
            (
                "Distinct alternate corridor offering a middle trade-off "
                "between travel distance and roadway safety score."
            ),
            elevation_gain_m=18.0 + straight_km * 2.4,
            routing_source=balanced_item[3],
        )

    result["Direct"] = package_route_option(
        "Direct",
        retag_route_segments(direct_item[2], "osm_dir"),
        planned_speed_mph,
        start_time_24h,
        (
            "Shortest distinct corridor between your start and end locations; "
            "all roads are scored with the exact same objective safety rules."
        ),
        elevation_gain_m=22.0 + straight_km * 2.7,
        routing_source=direct_item[3],
    )
    return result


@functools.lru_cache(maxsize=64)
def fetch_osrm_routes(
    coord_pairs: Tuple[Tuple[float, float], ...], profile: str = "bike"
) -> Tuple[Dict[str, Any], ...]:
    """Query FOSSGIS OpenStreetMap OSRM for road-following GeoJSON routes.

    Note: Cannot be unit tested offline because it depends on a live HTTP
    network call to routing.openstreetmap.de.
    """
    profile_path = "routed-bike" if profile == "bike" else "routed-car"
    coord_text = ";".join(f"{lon:.5f},{lat:.5f}" for lat, lon in coord_pairs)
    alts_flag = "3" if len(coord_pairs) == 2 else "false"
    url = (
        f"https://routing.openstreetmap.de/{profile_path}/route/v1/driving/"
        f"{coord_text}?overview=false&geometries=geojson&steps=true"
        f"&alternatives={alts_flag}"
    )
    payload = fetch_json_url(url, timeout_secs=4.0)
    if isinstance(payload, dict) and payload.get("code") == "Ok":
        routes = payload.get("routes") or []
        if isinstance(routes, list) and routes:
            return tuple(routes)
    return ()


def plan_live_osrm_routes(
    start_coord: Coordinate,
    dest_coord: Coordinate,
    planned_speed_mph: float,
    start_time_24h: str,
    detour_tolerance: str = "50%",
) -> Optional[Dict[str, RouteOption]]:
    """Build up to 3 genuinely distinct scored routes via live OSRM.

    Note: Cannot be unit tested offline because it calls live OSRM HTTP APIs
    via `fetch_osrm_routes`.
    """
    straight_km = calculate_haversine_distance_km(start_coord, dest_coord)
    if straight_km < 0.15 or straight_km > 250.0:
        return None

    base_pair = (
        (round(start_coord.latitude, 5), round(start_coord.longitude, 5)),
        (round(dest_coord.latitude, 5), round(dest_coord.longitude, 5)),
    )
    bike_routes = fetch_osrm_routes(base_pair, profile="bike")
    if not bike_routes:
        return None

    candidates: List[Tuple[List[RoadSegment], str]] = []
    for idx, raw_rt in enumerate(bike_routes[:3], start=1):
        segs = build_segments_from_osrm_route(raw_rt, f"bike_{idx}")
        if segs:
            candidates.append(
                (segs, "Live OpenStreetMap Bicycle Routing (OSRM)")
            )

    direct_routes = fetch_osrm_routes(base_pair, profile="car")
    for idx, raw_rt in enumerate(direct_routes[:2], start=1):
        segs = build_segments_from_osrm_route(raw_rt, f"car_{idx}")
        if segs:
            candidates.append(
                (segs, "Live OpenStreetMap Street Routing (OSRM)")
            )

    if len(bike_routes) < 3:
        for via_idx, offset in enumerate((0.18, -0.18), start=1):
            via_pt = compute_via_waypoint(start_coord, dest_coord, offset)
            via_pair = (
                base_pair[0],
                (via_pt.latitude, via_pt.longitude),
                base_pair[1],
            )
            alt_routes = fetch_osrm_routes(via_pair, profile="bike")
            if alt_routes:
                segs = build_segments_from_osrm_route(
                    alt_routes[0], f"via_{via_idx}"
                )
                if segs:
                    candidates.append(
                        (segs, "Live OpenStreetMap Bicycle Routing (OSRM)")
                    )

    selected = select_distinct_ranked_routes(
        candidates,
        planned_speed_mph,
        start_time_24h,
        detour_tolerance,
        straight_km,
    )
    return selected if selected else None


class SafetyRoutingGraph:
    """Weighted cycling network graph supporting safety-aware Dijkstra search."""

    def __init__(self) -> None:
        """Initialize empty graph node and adjacency-list edge dictionaries."""
        self.nodes: Dict[str, Coordinate] = {}
        self.edges: Dict[str, List[Tuple[str, RoadSegment]]] = {}

    def add_node(self, node_id: str, coordinate: Coordinate) -> None:
        """Register a named intersection node with its geographic Coordinate."""
        self.nodes[node_id] = coordinate
        self.edges.setdefault(node_id, [])

    def add_edge(
        self,
        source_node: str,
        target_node: str,
        segment: RoadSegment,
        bidirectional: bool = True,
    ) -> None:
        """Connect two graph nodes with an evaluated cycling RoadSegment."""
        self.edges.setdefault(source_node, []).append((target_node, segment))
        if bidirectional:
            reverse_segment = RoadSegment(
                segment_id=f"{segment.segment_id}_rev",
                name=segment.name,
                coordinates=list(reversed(segment.coordinates)),
                length_km=segment.length_km,
                infrastructure=segment.infrastructure,
                speed_limit_mph=segment.speed_limit_mph,
                traffic_exposure=segment.traffic_exposure,
                crash_record=segment.crash_record,
                intersection_risk=segment.intersection_risk,
                safety_score=segment.safety_score,
                confidence=segment.confidence,
                risk_category=segment.risk_category,
                positive_factors=list(segment.positive_factors),
                negative_factors=list(segment.negative_factors),
                evidence_notes=segment.evidence_notes,
                safer_alternative=segment.safer_alternative,
            )
            self.edges.setdefault(target_node, []).append(
                (source_node, reverse_segment)
            )

    def calculate_edge_cost(self, segment: RoadSegment, mode: str) -> float:
        """Compute mode-dependent traversal cost balancing distance and risk."""
        risk_penalty = max(0.0, (100.0 - segment.safety_score) / 100.0)
        if mode == "Safest":
            return segment.length_km * (1.0 + 5.2 * (risk_penalty**1.4))
        if mode == "Balanced":
            return segment.length_km * (1.0 + 0.65 * risk_penalty)
        return segment.length_km * (1.0 + 0.15 * risk_penalty)

    def find_shortest_safety_path(
        self, start_node: str, goal_node: str, mode: str
    ) -> List[RoadSegment]:
        """Run Dijkstra's algorithm to return the optimal RoadSegment path."""
        if start_node not in self.nodes or goal_node not in self.nodes:
            return []
        priority_queue: List[Tuple[float, str, List[RoadSegment]]] = [
            (0.0, start_node, [])
        ]
        lowest_cost: Dict[str, float] = {start_node: 0.0}

        while priority_queue:
            current_cost, current_node, current_path = heapq.heappop(
                priority_queue
            )
            if current_node == goal_node:
                return current_path
            if current_cost > lowest_cost.get(current_node, float("inf")):
                continue
            for neighbor_node, segment in self.edges.get(current_node, []):
                candidate_cost = current_cost + self.calculate_edge_cost(
                    segment, mode
                )
                if candidate_cost < lowest_cost.get(
                    neighbor_node, float("inf")
                ):
                    lowest_cost[neighbor_node] = candidate_cost
                    heapq.heappush(
                        priority_queue,
                        (candidate_cost, neighbor_node, current_path + [segment]),
                    )
        return []


def add_delaware_safest_edges(graph: SafetyRoutingGraph) -> None:
    """Attach separated greenway and canal trail segments to Delaware graph."""
    graph.add_edge(
        "start",
        "ud_green",
        make_evaluated_segment(
            "de_safe_1",
            "S College Ave Separated Cycle Track",
            [
                Coordinate(39.676456, -75.747050),
                Coordinate(39.6690, -75.7500),
                Coordinate(39.6620, -75.7520),
            ],
            2.4,
            "separated_lane",
            25,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    )
    graph.add_edge(
        "ud_green",
        "glasgow_park",
        make_evaluated_segment(
            "de_safe_2",
            "Pomeroy & Glasgow Park Multi-Use Greenway",
            [
                Coordinate(39.6620, -75.7520),
                Coordinate(39.6350, -75.7440),
                Coordinate(39.6107, -75.7290),
            ],
            6.8,
            "protected_bike_path",
            15,
            "very_low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    )
    graph.add_edge(
        "glasgow_park",
        "canal_west",
        make_evaluated_segment(
            "de_safe_3",
            "Lums Pond Connector Bikeway",
            [
                Coordinate(39.6107, -75.7290),
                Coordinate(39.5930, -75.7270),
                Coordinate(39.5790, -75.7240),
            ],
            4.5,
            "traffic_calmed_street",
            20,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    )
    graph.add_edge(
        "canal_west",
        "end",
        make_evaluated_segment(
            "de_safe_4",
            "Michael Castle C&D Canal Trail East",
            [
                Coordinate(39.5790, -75.7240),
                Coordinate(39.5750, -75.7100),
                Coordinate(39.571807, -75.696079),
            ],
            4.8,
            "protected_bike_path",
            15,
            "very_low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    )


def add_delaware_balanced_edges(graph: SafetyRoutingGraph) -> None:
    """Attach painted bike lane and shoulder segments to the Delaware graph."""
    graph.add_edge(
        "start",
        "brookside",
        make_evaluated_segment(
            "de_bal_1",
            "Marrow Rd & Brookside Neighborhood Connector",
            [
                Coordinate(39.676456, -75.747050),
                Coordinate(39.6620, -75.7410),
                Coordinate(39.6480, -75.7360),
            ],
            3.6,
            "painted_lane",
            25,
            "moderate",
            CrashRecord(1, 0, 0, "2022-2025"),
            "moderate",
            safer_alternative=(
                "Use S College Ave Separated Cycle Track 0.4 mi west."
            ),
        ),
    )
    graph.add_edge(
        "brookside",
        "wilson_rd",
        make_evaluated_segment(
            "de_bal_2",
            "Old Baltimore Pike Paved Bike Shoulder",
            [
                Coordinate(39.6480, -75.7360),
                Coordinate(39.6350, -75.7250),
                Coordinate(39.6220, -75.7160),
            ],
            4.2,
            "paved_shoulder",
            30,
            "moderate",
            CrashRecord(1, 0, 0, "2022-2025"),
            "moderate",
            safer_alternative=(
                "Detour onto Pomeroy & Glasgow Park Multi-Use Greenway."
            ),
        ),
    )
    graph.add_edge(
        "wilson_rd",
        "porter_rd",
        make_evaluated_segment(
            "de_bal_3",
            "Salem Church & Porter Rd Painted Bike Lane",
            [
                Coordinate(39.6220, -75.7160),
                Coordinate(39.6060, -75.7060),
                Coordinate(39.5910, -75.6990),
            ],
            4.4,
            "painted_lane",
            30,
            "moderate",
            CrashRecord(0, 0, 0, "2022-2025"),
            "moderate",
        ),
    )
    graph.add_edge(
        "porter_rd",
        "end",
        make_evaluated_segment(
            "de_bal_4",
            "Woodside Manor & Kirkwood Local Connector",
            [
                Coordinate(39.5910, -75.6990),
                Coordinate(39.5810, -75.6975),
                Coordinate(39.571807, -75.696079),
            ],
            3.1,
            "traffic_calmed_street",
            25,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    )


def add_delaware_direct_edges(graph: SafetyRoutingGraph) -> None:
    """Attach high-speed arterial DE-896 / US-40 segments to Delaware graph."""
    graph.add_edge(
        "start",
        "rt896_mid",
        make_evaluated_segment(
            "de_dir_1",
            "DE-896 South College Arterial (I-95 Interchange)",
            [
                Coordinate(39.676456, -75.747050),
                Coordinate(39.6510, -75.7390),
                Coordinate(39.6250, -75.7310),
            ],
            6.3,
            "none",
            45,
            "heavy",
            CrashRecord(6, 2, 1, "2022-2025"),
            "high_conflict",
            safer_alternative=(
                "Avoid I-95 cloverleaf ramps via Glasgow Park Greenway."
            ),
        ),
    )
    graph.add_edge(
        "rt896_mid",
        "end",
        make_evaluated_segment(
            "de_dir_2",
            "US-40 & DE-896 Commercial Corridor",
            [
                Coordinate(39.6250, -75.7310),
                Coordinate(39.5980, -75.7130),
                Coordinate(39.571807, -75.696079),
            ],
            6.9,
            "shared_lane",
            40,
            "heavy",
            CrashRecord(4, 1, 0, "2022-2025"),
            "high_conflict",
            safer_alternative=(
                "Shift east to Porter Rd Bike Lane or west to Canal Trail."
            ),
        ),
    )


@functools.lru_cache(maxsize=2)
def build_default_corridor_graph() -> SafetyRoutingGraph:
    """Build deterministic Newark <-> Kirkwood Delaware benchmark graph."""
    graph = SafetyRoutingGraph()
    graph.add_node("start", NEWARK_ANCHOR)
    graph.add_node("ud_green", Coordinate(39.6620, -75.7520))
    graph.add_node("glasgow_park", Coordinate(39.6107, -75.7290))
    graph.add_node("canal_west", Coordinate(39.5790, -75.7240))
    graph.add_node("brookside", Coordinate(39.6480, -75.7360))
    graph.add_node("wilson_rd", Coordinate(39.6220, -75.7160))
    graph.add_node("porter_rd", Coordinate(39.5910, -75.6990))
    graph.add_node("rt896_mid", Coordinate(39.6250, -75.7310))
    graph.add_node("end", KIRKWOOD_ANCHOR)

    add_delaware_safest_edges(graph)
    add_delaware_balanced_edges(graph)
    add_delaware_direct_edges(graph)
    return graph


def collect_route_warnings(
    segments: List[RoadSegment], start_time_24h: str
) -> List[str]:
    """Assemble departure time and high-risk segment safety warnings."""
    warnings: List[str] = []
    time_note, time_multiplier = get_time_of_day_traffic_note(start_time_24h)
    if time_multiplier > 1.05:
        warnings.append(time_note)
    for segment in segments:
        if segment.risk_category == "HIGH_RISK":
            speed_display = segment.speed_limit_mph or "unknown"
            warnings.append(
                f"High-risk segment: {segment.name} "
                f"(Score {segment.safety_score:.0f}/100, {speed_display} mph)."
            )
        elif segment.risk_category == "UNKNOWN":
            warnings.append(
                f"Insufficient safety data on {segment.name}: "
                "exercise extra caution."
            )
    return warnings


def package_route_option(
    route_type: str,
    segments: List[RoadSegment],
    planned_speed_mph: float,
    start_time_24h: str,
    rationale: str,
    elevation_gain_m: float,
    routing_source: str = "Local Safety Graph",
) -> RouteOption:
    """Aggregate segment scores, distances, timing, and warnings."""
    total_km = round(sum(segment.length_km for segment in segments), 2)
    speed_kmh = max(8.0, planned_speed_mph * KM_PER_MILE)
    duration_mins = round((total_km / speed_kmh) * 60.0, 1)

    if total_km > 0:
        weighted_score = (
            sum(segment.safety_score * segment.length_km for segment in segments)
            / total_km
        )
    else:
        weighted_score = 0.0
    overall_score = round(weighted_score, 1)

    dedicated_km = sum(
        segment.length_km
        for segment in segments
        if segment.infrastructure in DEDICATED_BIKE_FACILITIES
    )
    infra_pct = (
        round((dedicated_km / total_km) * 100.0, 1) if total_km > 0 else 0.0
    )
    high_risk_count = sum(
        1
        for segment in segments
        if segment.risk_category in ("HIGH_RISK", "ELEVATED")
    )
    major_intersections = sum(
        2
        if segment.intersection_risk == "high_conflict"
        else (1 if segment.intersection_risk == "moderate" else 0)
        for segment in segments
    )

    warnings = collect_route_warnings(segments, start_time_24h)
    confidences = [segment.confidence for segment in segments]
    if "INSUFFICIENT" in confidences:
        confidence_level = "LOW"
    elif confidences.count("HIGH") >= max(1, len(confidences) // 2):
        confidence_level = "HIGH"
    else:
        confidence_level = "MEDIUM"

    corridor_names = [
        segment.name.split("(")[0].strip() for segment in segments[:3]
    ]
    summary = " -> ".join(corridor_names)

    return RouteOption(
        route_type=route_type,
        total_distance_km=total_km,
        estimated_duration_mins=duration_mins,
        overall_safety_score=overall_score,
        high_risk_segments_count=high_risk_count,
        bike_infrastructure_percentage=infra_pct,
        major_intersections_count=major_intersections,
        warnings=warnings,
        segments=segments,
        selection_rationale=rationale,
        confidence_level=confidence_level,
        elevation_gain_m=round(elevation_gain_m, 1),
        corridor_summary=summary,
        routing_source=routing_source,
    )


def interpolate_corridor_points(
    origin: Coordinate,
    destination: Coordinate,
    lateral_offset_deg: float,
    steps: int = 4,
) -> List[Coordinate]:
    """Generate smooth curved geographic waypoints between two endpoints."""
    delta_lat = destination.latitude - origin.latitude
    delta_lon = destination.longitude - origin.longitude
    span_length = math.hypot(delta_lat, delta_lon) or 0.001
    perp_lat = -delta_lon / span_length
    perp_lon = delta_lat / span_length
    waypoints: List[Coordinate] = []
    for step_index in range(steps + 1):
        fraction = step_index / float(steps)
        arc_offset = math.sin(math.pi * fraction) * lateral_offset_deg
        waypoints.append(
            Coordinate(
                round(
                    origin.latitude + delta_lat * fraction + perp_lat * arc_offset,
                    6,
                ),
                round(
                    origin.longitude + delta_lon * fraction + perp_lon * arc_offset,
                    6,
                ),
            )
        )
    return waypoints


def build_generic_safest_segments(
    origin: Coordinate,
    destination: Coordinate,
    start_short: str,
    dest_short: str,
    span_deg: float,
    straight_km: float,
) -> List[RoadSegment]:
    """Build protected greenway and cycle-track segments for offline fallback."""
    safe_points = interpolate_corridor_points(
        origin, destination, +span_deg, steps=4
    )
    safe_distance = straight_km * 1.24
    return [
        make_evaluated_segment(
            "safe_1",
            f"{start_short} Protected Cycle Track",
            safe_points[0:2],
            safe_distance * 0.24,
            "separated_lane",
            20,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
        make_evaluated_segment(
            "safe_2",
            "Regional Multi-Use Park Greenway",
            safe_points[1:3],
            safe_distance * 0.34,
            "protected_bike_path",
            15,
            "very_low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
        make_evaluated_segment(
            "safe_3",
            "Quiet Neighborhood Bike Boulevard",
            safe_points[2:4],
            safe_distance * 0.24,
            "traffic_calmed_street",
            20,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
        make_evaluated_segment(
            "safe_4",
            f"{dest_short} Greenway Approach",
            safe_points[3:5],
            safe_distance * 0.18,
            "separated_lane",
            20,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    ]


def build_generic_balanced_segments(
    origin: Coordinate,
    destination: Coordinate,
    start_short: str,
    dest_short: str,
    span_deg: float,
    straight_km: float,
) -> List[RoadSegment]:
    """Build painted bike lane and shoulder segments for offline fallback."""
    balanced_points = interpolate_corridor_points(
        origin, destination, -span_deg * 0.65, steps=3
    )
    balanced_distance = straight_km * 1.11
    return [
        make_evaluated_segment(
            "bal_1",
            f"{start_short} Painted Bike Lane",
            balanced_points[0:2],
            balanced_distance * 0.34,
            "painted_lane",
            25,
            "moderate",
            CrashRecord(1, 0, 0, "2022-2025"),
            "moderate",
            safer_alternative=(
                "Detour onto Regional Multi-Use Park Greenway for separation."
            ),
        ),
        make_evaluated_segment(
            "bal_2",
            "Mid-Corridor Collector Bike Shoulder",
            balanced_points[1:3],
            balanced_distance * 0.36,
            "paved_shoulder",
            30,
            "moderate",
            CrashRecord(1, 0, 0, "2022-2025"),
            "moderate",
            safer_alternative="Use Quiet Neighborhood Bike Boulevard instead.",
        ),
        make_evaluated_segment(
            "bal_3",
            f"{dest_short} Connector Bike Lane",
            balanced_points[2:4],
            balanced_distance * 0.30,
            "painted_lane",
            25,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        ),
    ]


def build_generic_direct_segments(
    origin: Coordinate,
    destination: Coordinate,
    start_short: str,
    dest_short: str,
    straight_km: float,
) -> List[RoadSegment]:
    """Build shortest arterial segments for Direct mode offline fallback."""
    direct_points = interpolate_corridor_points(
        origin, destination, 0.0, steps=3
    )
    direct_distance = straight_km * 1.02
    return [
        make_evaluated_segment(
            "dir_1",
            f"{start_short} Main Arterial Highway",
            direct_points[0:2],
            direct_distance * 0.42,
            "none",
            40,
            "heavy",
            CrashRecord(5, 2, 0, "2022-2025"),
            "high_conflict",
            safer_alternative=(
                "Switch to Safest mode to avoid high-speed arterial traffic."
            ),
        ),
        make_evaluated_segment(
            "dir_2",
            "Commercial Thruway (Unverified Speed Data)",
            direct_points[1:3],
            direct_distance * 0.33,
            "shared_lane",
            None,
            "high",
            None,
            "high_conflict",
            safer_alternative=(
                "Use Mid-Corridor Collector Bike Shoulder instead."
            ),
        ),
        make_evaluated_segment(
            "dir_3",
            f"{dest_short} Direct Approach",
            direct_points[2:4],
            direct_distance * 0.25,
            "painted_lane",
            30,
            "moderate",
            CrashRecord(1, 0, 0, "2022-2025"),
            "moderate",
        ),
    ]


def build_generic_corridor_routes(
    origin: Coordinate,
    destination: Coordinate,
    start_label: str,
    dest_label: str,
    planned_speed_mph: float,
    start_time_24h: str,
) -> Dict[str, RouteOption]:
    """Synthesize offline Safest, Balanced, and Direct corridors."""
    straight_km = calculate_haversine_distance_km(origin, destination)
    if straight_km < 0.15:
        local_segment = make_evaluated_segment(
            "local_1",
            f"Local Access near {start_label.split(',')[0]}",
            [origin, destination],
            max(0.2, straight_km),
            "traffic_calmed_street",
            20,
            "low",
            CrashRecord(0, 0, 0, "2022-2025"),
            "low",
        )
        single_route = package_route_option(
            "Safest",
            [local_segment],
            planned_speed_mph,
            start_time_24h,
            (
                "Start and destination are less than 150 m apart; only one "
                "short local corridor is needed."
            ),
            4.0,
        )
        return {"Safest": single_route}

    coord_span = math.hypot(
        destination.latitude - origin.latitude,
        destination.longitude - origin.longitude,
    )
    span_deg = max(0.004, min(0.035, coord_span * 0.22))
    start_short = start_label.split(",")[0].strip()
    dest_short = dest_label.split(",")[0].strip()

    safe_segments = build_generic_safest_segments(
        origin, destination, start_short, dest_short, span_deg, straight_km
    )
    balanced_segments = build_generic_balanced_segments(
        origin, destination, start_short, dest_short, span_deg, straight_km
    )
    direct_segments = build_generic_direct_segments(
        origin, destination, start_short, dest_short, straight_km
    )

    return {
        "Safest": package_route_option(
            "Safest",
            safe_segments,
            planned_speed_mph,
            start_time_24h,
            (
                "Prioritizes physically separated paths and traffic-calmed "
                "greenways, accepting a modest detour to reduce vehicle risk."
            ),
            elevation_gain_m=18.0 + straight_km * 2.2,
        ),
        "Balanced": package_route_option(
            "Balanced",
            balanced_segments,
            planned_speed_mph,
            start_time_24h,
            (
                "Balances moderate cycling time with painted bike lanes and "
                "paved shoulders while avoiding high-speed arterials."
            ),
            elevation_gain_m=22.0 + straight_km * 2.5,
        ),
        "Direct": package_route_option(
            "Direct",
            direct_segments,
            planned_speed_mph,
            start_time_24h,
            (
                "Shortest distance corridor. High-speed mixed-traffic segments "
                "and missing data are explicitly flagged rather than hidden."
            ),
            elevation_gain_m=28.0 + straight_km * 2.8,
        ),
    }


@functools.lru_cache(maxsize=24)
def plan_bicycle_routes_cached(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    start_label: str,
    dest_label: str,
    parsed_speed: float,
    start_time_24h: str,
    detour_tolerance: str,
    allow_remote: bool,
) -> Dict[str, RouteOption]:
    """Cached core route planner so tab switches and toggles are instant."""
    start_coord = Coordinate(start_lat, start_lon)
    dest_coord = Coordinate(dest_lat, dest_lon)
    routes: Optional[Dict[str, RouteOption]] = None

    if allow_remote:
        routes = plan_live_osrm_routes(
            start_coord,
            dest_coord,
            parsed_speed,
            start_time_24h,
            detour_tolerance,
        )

    if routes is None:
        is_delaware_corridor = (
            calculate_haversine_distance_km(start_coord, NEWARK_ANCHOR) < 2.0
            and calculate_haversine_distance_km(dest_coord, KIRKWOOD_ANCHOR)
            < 3.0
        )
        if is_delaware_corridor:
            graph = build_default_corridor_graph()
            safest_segs = graph.find_shortest_safety_path(
                "start", "end", "Safest"
            )
            balanced_segs = graph.find_shortest_safety_path(
                "start", "end", "Balanced"
            )
            direct_segs = graph.find_shortest_safety_path(
                "start", "end", "Direct"
            )
            routes = {
                "Safest": package_route_option(
                    "Safest",
                    safest_segs,
                    parsed_speed,
                    start_time_24h,
                    (
                        "Uses S College Ave Separated Cycle Track, Pomeroy / "
                        "Glasgow Park Greenway, and C&D Canal Trail."
                    ),
                    elevation_gain_m=46.0,
                ),
                "Balanced": package_route_option(
                    "Balanced",
                    balanced_segs,
                    parsed_speed,
                    start_time_24h,
                    (
                        "Uses Brookside neighborhood streets, Old Baltimore "
                        "Pike paved shoulder, and Porter Rd bike lanes."
                    ),
                    elevation_gain_m=58.0,
                ),
                "Direct": package_route_option(
                    "Direct",
                    direct_segs,
                    parsed_speed,
                    start_time_24h,
                    (
                        "Direct DE-896 / US-40 corridor saves distance but "
                        "rides on 40-45 mph heavy-traffic segments."
                    ),
                    elevation_gain_m=64.0,
                ),
            }
        else:
            routes = build_generic_corridor_routes(
                start_coord,
                dest_coord,
                start_label,
                dest_label,
                parsed_speed,
                start_time_24h,
            )

    max_ratio = parse_detour_ratio(detour_tolerance)
    if "Safest" in routes and "Direct" in routes:
        direct_km = max(0.1, routes["Direct"].total_distance_km)
        actual_ratio = routes["Safest"].total_distance_km / direct_km
        if actual_ratio > max_ratio:
            detour_pct = (actual_ratio - 1.0) * 100.0
            warning_msg = (
                f"Detour length (+{detour_pct:.0f}%) exceeds your "
                f"{detour_tolerance} detour tolerance; Balanced mode may fit."
            )
            if warning_msg not in routes["Safest"].warnings:
                routes["Safest"].warnings.append(warning_msg)

    return routes


def plan_bicycle_routes(
    start_coord: Coordinate,
    dest_coord: Coordinate,
    start_label: str,
    dest_label: str,
    planned_speed_mph: float = 12.0,
    start_time_24h: str = "08:30",
    detour_tolerance: str = "50%",
    allow_remote: bool = False,
) -> Dict[str, RouteOption]:
    """Generate Safest, Balanced, and Direct bicycle route options."""
    parsed_speed = parse_speed_mph(planned_speed_mph)
    return plan_bicycle_routes_cached(
        round(start_coord.latitude, 5),
        round(start_coord.longitude, 5),
        round(dest_coord.latitude, 5),
        round(dest_coord.longitude, 5),
        start_label,
        dest_label,
        parsed_speed,
        start_time_24h,
        detour_tolerance,
        allow_remote,
    )


def recalibrate_routes_for_speed(
    routes: Dict[str, RouteOption], planned_speed_mph: float
) -> Dict[str, RouteOption]:
    """Recalculate estimated cycling durations for a new planned speed."""
    parsed_speed = parse_speed_mph(planned_speed_mph)
    speed_kmh = max(8.0, parsed_speed * KM_PER_MILE)
    updated_routes: Dict[str, RouteOption] = {}
    for mode_key, route_option in routes.items():
        new_minutes = round(
            (route_option.total_distance_km / speed_kmh) * 60.0, 1
        )
        updated_routes[mode_key] = RouteOption(
            route_type=route_option.route_type,
            total_distance_km=route_option.total_distance_km,
            estimated_duration_mins=new_minutes,
            overall_safety_score=route_option.overall_safety_score,
            high_risk_segments_count=route_option.high_risk_segments_count,
            bike_infrastructure_percentage=(
                route_option.bike_infrastructure_percentage
            ),
            major_intersections_count=route_option.major_intersections_count,
            warnings=list(route_option.warnings),
            segments=list(route_option.segments),
            selection_rationale=route_option.selection_rationale,
            confidence_level=route_option.confidence_level,
            elevation_gain_m=route_option.elevation_gain_m,
            corridor_summary=route_option.corridor_summary,
            routing_source=route_option.routing_source,
        )
    return updated_routes
