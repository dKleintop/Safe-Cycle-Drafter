"""visuals.py - Route polyline serialization and pure-Python SVG safety charts.

Advanced technique notes:
- Projects geographic latitude/longitude coordinates linearly into 2D SVG
  pixel coordinates for Drafter's native `SVG(...)` component.
- Serializes risk-colored road-following route polylines to JSON for
  `<drafter-map>`'s Leaflet overlay so real street routes draw cleanly on
  OpenStreetMap tiles instead of disconnected circle markers.
"""

import json
import math
from typing import Any, Dict, List, Optional, Tuple
from models import Coordinate, RoadSegment, RouteOption
from safety import determine_risk_category, get_risk_color_hex

LEGEND_ITEMS: List[Tuple[str, str]] = [
    ("Lower Risk 80+", "#15803d"),
    ("Moderate 60-79", "#b45309"),
    ("Elevated 40-59", "#c2410c"),
    ("High Risk <40", "#b91c1c"),
    ("Unknown", "#64748b"),
]


def escape_svg_text(raw_text: str) -> str:
    """Escape XML entities for safe SVG text elements."""
    return (
        raw_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def collect_route_coordinates(
    routes: Dict[str, RouteOption],
) -> List[Coordinate]:
    """Gather all geographic coordinates across candidate route options."""
    coordinates: List[Coordinate] = []
    for route_option in routes.values():
        for segment in route_option.segments:
            coordinates.extend(segment.coordinates)
    return coordinates


def flatten_option_points(route_option: RouteOption) -> List[Tuple[float, float]]:
    """Flatten a RouteOption's segments into a list of (lat, lon) tuples."""
    pts: List[Tuple[float, float]] = []
    for segment in route_option.segments:
        for coord in segment.coordinates:
            pair = (coord.latitude, coord.longitude)
            if not pts or pts[-1] != pair:
                pts.append(pair)
    return pts


ROUTE_SHORT_LABELS: Dict[str, str] = {
    "Safest": "Saf",
    "Balanced": "Bal",
    "Direct": "Dir",
}

BADGE_FRACTIONS: Tuple[float, ...] = (0.30, 0.52, 0.72)


def get_route_short_label(route_type: str) -> str:
    """Return a compact 3-letter abbreviation for a route mode name."""
    return ROUTE_SHORT_LABELS.get(route_type, route_type[:3])


def find_distinct_badge_point(
    target_route: RouteOption,
    routes: Dict[str, RouteOption],
    used_points: List[Tuple[float, float]],
    preferred_fraction: float = 0.5,
) -> Optional[Tuple[float, float]]:
    """Pick an interior map coordinate well away from S/E pins and peers."""
    pts = flatten_option_points(target_route)
    if not pts:
        return None
    if len(pts) <= 2:
        return (
            (pts[0][0] + pts[-1][0]) / 2.0,
            (pts[0][1] + pts[-1][1]) / 2.0,
        )

    start_pt = pts[0]
    end_pt = pts[-1]
    span_deg = max(
        math.hypot(end_pt[0] - start_pt[0], end_pt[1] - start_pt[1]),
        0.004,
    )
    min_endpoint_gap = span_deg * 0.22

    start_idx = max(1, int(len(pts) * 0.22))
    end_idx = min(len(pts) - 1, max(start_idx + 1, int(len(pts) * 0.78)))
    interior = pts[start_idx:end_idx] or pts[1:-1] or pts

    other_pts: List[Tuple[float, float]] = []
    for mode_name, other_route in routes.items():
        if mode_name == target_route.route_type:
            continue
        other_pts.extend(flatten_option_points(other_route))

    if not other_pts and not used_points:
        target_idx = int(round((len(interior) - 1) * preferred_fraction))
        return interior[max(0, min(len(interior) - 1, target_idx))]

    best_pt = interior[len(interior) // 2]
    best_rank = -1.0
    for idx, pt in enumerate(interior):
        endpoint_clearance = min(
            math.hypot(pt[0] - start_pt[0], pt[1] - start_pt[1]),
            math.hypot(pt[0] - end_pt[0], pt[1] - end_pt[1]),
        )
        endpoint_weight = (
            0.25 if endpoint_clearance < min_endpoint_gap else 1.0
        )
        min_route_sep = (
            min(
                math.hypot(pt[0] - opt[0], pt[1] - opt[1]) for opt in other_pts
            )
            if other_pts
            else 0.02
        )
        min_badge_sep = (
            min(
                math.hypot((pt[0] - upt[0]) * 1.8, (pt[1] - upt[1]) * 0.7)
                for upt in used_points
            )
            if used_points
            else 0.05
        )
        frac = idx / max(1, len(interior) - 1)
        stagger_bias = 1.0 - abs(frac - preferred_fraction) * 0.35
        rank = (
            (min_route_sep + min_badge_sep * 2.2)
            * stagger_bias
            * endpoint_weight
        )
        if rank > best_rank:
            best_rank = rank
            best_pt = pt
    return best_pt


def build_map_polylines_json(
    routes: Dict[str, RouteOption], active_mode: str
) -> str:
    """Serialize clean continuous route polylines and compact map badges."""
    payload: List[Dict[str, Any]] = []
    active_route = routes.get(active_mode) or (
        next(iter(routes.values())) if routes else None
    )
    active_key = active_route.route_type if active_route is not None else ""

    for mode_name, route_option in routes.items():
        if mode_name == active_key:
            continue
        alt_coords = [
            [lat, lon] for lat, lon in flatten_option_points(route_option)
        ]
        if len(alt_coords) >= 2:
            payload.append(
                {
                    "kind": "line",
                    "routeMode": mode_name,
                    "isActive": False,
                    "coords": alt_coords,
                    "color": "#64748b",
                    "weight": 4.5,
                    "opacity": 0.72,
                    "dashArray": "",
                    "label": (
                        f"{mode_name} · Safety "
                        f"{route_option.overall_safety_score:.0f}/100"
                    ),
                }
            )

    if active_route is not None:
        active_coords = [
            [lat, lon] for lat, lon in flatten_option_points(active_route)
        ]
        if len(active_coords) >= 2:
            payload.append(
                {
                    "kind": "line",
                    "routeMode": active_key,
                    "isActive": True,
                    "coords": active_coords,
                    "color": "#047857",
                    "weight": 6,
                    "opacity": 0.96,
                    "dashArray": "",
                    "label": (
                        f"{active_key} Route · Safety "
                        f"{active_route.overall_safety_score:.0f}/100"
                    ),
                }
            )

    placed_badges: List[Tuple[float, float]] = []
    for badge_idx, (mode_name, route_option) in enumerate(routes.items()):
        pref_frac = BADGE_FRACTIONS[badge_idx % len(BADGE_FRACTIONS)]
        badge_pt = find_distinct_badge_point(
            route_option, routes, placed_badges, preferred_fraction=pref_frac
        )
        if badge_pt is None:
            continue
        placed_badges.append(badge_pt)
        risk_cat = determine_risk_category(
            route_option.overall_safety_score, route_option.confidence_level
        )
        score_text = f"{route_option.overall_safety_score:.0f}"
        short_name = get_route_short_label(mode_name)
        payload.append(
            {
                "kind": "badge",
                "routeMode": mode_name,
                "active": mode_name == active_key,
                "lat": round(badge_pt[0], 6),
                "lon": round(badge_pt[1], 6),
                "shortText": f"{short_name} · {score_text}",
                "fullText": f"{mode_name} · {score_text}",
                "text": f"{mode_name} · {score_text}",
                "color": get_risk_color_hex(risk_cat),
            }
        )

    return json.dumps(payload, separators=(",", ":"))


def build_segment_polyline_json(segment: RoadSegment) -> str:
    """Serialize a single inspected RoadSegment into Leaflet polyline JSON."""
    coords = [
        [coord.latitude, coord.longitude] for coord in segment.coordinates
    ]
    if len(coords) < 2:
        return "[]"
    return json.dumps(
        [
            {
                "kind": "line",
                "isActive": True,
                "coords": coords,
                "color": get_risk_color_hex(segment.risk_category),
                "weight": 7,
                "opacity": 0.95,
                "dashArray": "",
                "label": (
                    f"{segment.name} · Score {segment.safety_score:.0f}/100"
                ),
            }
        ],
        separators=(",", ":"),
    )


def project_coordinate(
    coordinate: Coordinate,
    bounds: Tuple[float, float, float, float],
    plot_box: Tuple[float, float, float, float],
) -> Tuple[float, float]:
    """Project a geographic Coordinate into (x, y) SVG viewport pixels."""
    min_lat, lat_span, min_lon, lon_span = bounds
    pad_x, pad_top, plot_w, plot_h = plot_box
    pixel_x = pad_x + ((coordinate.longitude - min_lon) / lon_span) * plot_w
    pixel_y = (
        pad_top
        + (1.0 - ((coordinate.latitude - min_lat) / lat_span)) * plot_h
    )
    return (round(pixel_x, 1), round(pixel_y, 1))


def build_svg_grid_lines(
    pad_x: int,
    pad_top: int,
    pad_bottom: int,
    width: int,
    height: int,
    grid_stroke: str,
) -> List[str]:
    """Generate subtle dashed reference grid lines for the corridor SVG."""
    plot_w = width - 2 * pad_x
    plot_h = height - pad_top - pad_bottom
    lines: List[str] = []
    for step in range(1, 5):
        grid_x = round(pad_x + (plot_w * step) / 5.0, 1)
        grid_y = round(pad_top + (plot_h * step) / 5.0, 1)
        lines.append(
            f'<line x1="{grid_x}" y1="{pad_top}" x2="{grid_x}" '
            f'y2="{height - pad_bottom}" stroke="{grid_stroke}" '
            'stroke-width="1" stroke-dasharray="3 4"/>'
        )
        lines.append(
            f'<line x1="{pad_x}" y1="{grid_y}" x2="{width - pad_x}" '
            f'y2="{grid_y}" stroke="{grid_stroke}" '
            'stroke-width="1" stroke-dasharray="3 4"/>'
        )
    return lines


def build_svg_legend(height: int, text_muted: str) -> List[str]:
    """Generate bottom color-coded risk band legend elements for SVG."""
    elements: List[str] = []
    cursor_x = 16.0
    baseline_y = height - 16
    for label, color in LEGEND_ITEMS:
        elements.append(
            f'<rect x="{cursor_x}" y="{baseline_y - 9}" width="10" '
            f'height="10" rx="2" fill="{color}"/>'
        )
        elements.append(
            f'<text x="{cursor_x + 15}" y="{baseline_y}" font-size="10.5" '
            f'fill="{text_muted}">{escape_svg_text(label)}</text>'
        )
        cursor_x += len(label) * 6.5 + 30.0
    return elements


def build_corridor_comparison_svg(
    routes: Dict[str, RouteOption],
    active_mode: str,
    width: int = 640,
    height: int = 340,
    dark_mode: bool = False,
) -> str:
    """Build a pure SVG route corridor map with color-coded safety segments."""
    all_coordinates = collect_route_coordinates(routes)
    bg_color = "#0f172a" if dark_mode else "#f8fafc"
    grid_stroke = "#1e293b" if dark_mode else "#e2e8f0"
    text_main = "#f1f5f9" if dark_mode else "#0f172a"
    text_muted = "#94a3b8" if dark_mode else "#475569"
    inactive_stroke = "#475569" if dark_mode else "#cbd5e1"

    if not all_coordinates:
        return (
            f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
            f'fill="{bg_color}"/>'
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="{text_muted}" font-size="14">'
            "No route coordinates available</text>"
        )

    latitudes = [coord.latitude for coord in all_coordinates]
    longitudes = [coord.longitude for coord in all_coordinates]
    min_lat = min(latitudes)
    min_lon = min(longitudes)
    lat_span = max(max(latitudes) - min_lat, 0.006)
    lon_span = max(max(longitudes) - min_lon, 0.006)
    bounds = (min_lat, lat_span, min_lon, lon_span)

    pad_x = 56
    pad_top = 42
    pad_bottom = 52
    plot_box = (
        float(pad_x),
        float(pad_top),
        float(width - 2 * pad_x),
        float(height - pad_top - pad_bottom),
    )

    parts: List[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
        f'fill="{bg_color}" stroke="{grid_stroke}" stroke-width="1"/>'
    ]
    parts.extend(
        build_svg_grid_lines(
            pad_x, pad_top, pad_bottom, width, height, grid_stroke
        )
    )

    for mode_name, route_option in routes.items():
        if mode_name == active_mode:
            continue
        point_strings: List[str] = []
        for segment in route_option.segments:
            for coord in segment.coordinates:
                px, py = project_coordinate(coord, bounds, plot_box)
                point_strings.append(f"{px},{py}")
        if len(point_strings) >= 2:
            joined_pts = " ".join(point_strings)
            parts.append(
                f'<polyline points="{joined_pts}" fill="none" '
                f'stroke="{inactive_stroke}" stroke-width="4" '
                'stroke-linecap="round" stroke-linejoin="round" '
                'stroke-dasharray="6 5" opacity="0.85"/>'
            )

    active_route = routes.get(active_mode) or next(iter(routes.values()))
    start_pixel: Tuple[float, float] = (float(pad_x), float(pad_top))
    end_pixel: Tuple[float, float] = (
        float(width - pad_x),
        float(height - pad_bottom),
    )

    for segment_index, segment in enumerate(active_route.segments):
        projected_pts = [
            project_coordinate(coord, bounds, plot_box)
            for coord in segment.coordinates
        ]
        if not projected_pts:
            continue
        if segment_index == 0:
            start_pixel = projected_pts[0]
        end_pixel = projected_pts[-1]
        color = get_risk_color_hex(segment.risk_category)
        pts_attr = " ".join(f"{x},{y}" for x, y in projected_pts)
        parts.append(
            f'<polyline points="{pts_attr}" fill="none" stroke="{bg_color}" '
            'stroke-width="10" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
        )
        parts.append(
            f'<polyline points="{pts_attr}" fill="none" stroke="{color}" '
            'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    parts.append(
        f'<circle cx="{start_pixel[0]}" cy="{start_pixel[1]}" r="8" '
        'fill="#047857" stroke="#ffffff" stroke-width="2.5"/>'
    )
    parts.append(
        f'<text x="{start_pixel[0]}" y="{start_pixel[1] - 13:.1f}" '
        f'text-anchor="middle" font-size="11" font-weight="700" '
        f'fill="{text_main}">Start</text>'
    )
    parts.append(
        f'<circle cx="{end_pixel[0]}" cy="{end_pixel[1]}" r="8" '
        'fill="#dc2626" stroke="#ffffff" stroke-width="2.5"/>'
    )
    dest_label_y = min(height - pad_bottom + 16.0, end_pixel[1] + 20.0)
    parts.append(
        f'<text x="{end_pixel[0]}" y="{dest_label_y:.1f}" '
        f'text-anchor="middle" font-size="11" font-weight="700" '
        f'fill="{text_main}">Destination</text>'
    )
    parts.append(
        f'<text x="16" y="24" font-size="12" font-weight="700" '
        f'fill="{text_main}">Active Corridor: '
        f"{escape_svg_text(active_route.route_type)} "
        f"(Score {active_route.overall_safety_score:.0f}/100)</text>"
    )
    parts.extend(build_svg_legend(height, text_muted))
    return "\n".join(parts)


def build_safety_profile_svg(
    route: RouteOption,
    width: int = 1120,
    height: int = 155,
    dark_mode: bool = False,
) -> str:
    """Build a pure SVG horizontal segment-by-segment safety score bar chart."""
    bg_color = "#0f172a" if dark_mode else "#f8fafc"
    border_color = "#1e293b" if dark_mode else "#e2e8f0"
    text_main = "#f1f5f9" if dark_mode else "#0f172a"
    text_muted = "#94a3b8" if dark_mode else "#475569"

    parts: List[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" '
        f'fill="{bg_color}" stroke="{border_color}" stroke-width="1"/>',
        f'<text x="16" y="22" font-size="12" font-weight="700" '
        f'fill="{text_main}">Segment Safety Spectrum '
        f"({escape_svg_text(route.route_type)} Route)</text>",
    ]

    if not route.segments:
        return "\n".join(parts)

    total_km = max(sum(seg.length_km for seg in route.segments), 0.1)
    bar_x = 16.0
    bar_y = 36.0
    bar_width = float(width - 32)
    bar_height = 72.0

    y_80 = bar_y + bar_height * 0.20
    y_40 = bar_y + bar_height * 0.60
    parts.append(
        f'<line x1="{bar_x}" y1="{y_80:.1f}" x2="{bar_x + bar_width}" '
        f'y2="{y_80:.1f}" stroke="{border_color}" stroke-dasharray="3 3"/>'
    )
    parts.append(
        f'<line x1="{bar_x}" y1="{y_40:.1f}" x2="{bar_x + bar_width}" '
        f'y2="{y_40:.1f}" stroke="{border_color}" stroke-dasharray="3 3"/>'
    )

    cursor_x = bar_x
    for segment in route.segments:
        seg_width = max(24.0, (segment.length_km / total_km) * bar_width)
        if cursor_x + seg_width > bar_x + bar_width:
            seg_width = max(8.0, (bar_x + bar_width) - cursor_x)
        height_ratio = max(0.12, min(1.0, segment.safety_score / 100.0))
        rect_height = bar_height * height_ratio
        rect_y = bar_y + (bar_height - rect_height)
        color = get_risk_color_hex(segment.risk_category)
        parts.append(
            f'<rect x="{cursor_x + 1:.1f}" y="{rect_y:.1f}" '
            f'width="{max(4.0, seg_width - 3):.1f}" height="{rect_height:.1f}" '
            f'rx="4" fill="{color}" opacity="0.9"/>'
        )
        if seg_width >= 36:
            center_x = cursor_x + seg_width / 2.0
            parts.append(
                f'<text x="{center_x:.1f}" y="{rect_y + 15:.1f}" '
                'text-anchor="middle" font-size="10.5" font-weight="700" '
                f'fill="#ffffff">{segment.safety_score:.0f}</text>'
            )
            short_label = segment.name.split(" ")[0][:10]
            parts.append(
                f'<text x="{center_x:.1f}" y="{bar_y + bar_height + 16:.1f}" '
                f'text-anchor="middle" font-size="10" fill="{text_muted}">'
                f"{escape_svg_text(short_label)}</text>"
            )
        cursor_x += seg_width

    parts.append(
        f'<text x="16" y="{height - 10}" font-size="10.5" '
        f'fill="{text_muted}">Elevation gain: +{route.elevation_gain_m:.0f} m '
        "· Dedicated bike infrastructure: "
        f"{route.bike_infrastructure_percentage:.0f}%</text>"
    )
    return "\n".join(parts)
