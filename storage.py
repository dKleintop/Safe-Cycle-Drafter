"""storage.py - GPX 1.1 XML route export utilities for SafeCycle.

Advanced technique note:
- Formats real road-following geographic route segments into standard GPX 1.1
  XML with entity escaping so cyclists can download routes directly into bike
  computers and GPS apps without external XML libraries.
"""

import time
from typing import List
from models import RouteOption


def xml_escape(raw_text: str) -> str:
    """Escape XML special characters for safe GPX output."""
    return (
        raw_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_route_to_gpx(
    route: RouteOption, start_name: str, dest_name: str
) -> str:
    """Generate a valid GPX 1.1 XML string for GPS cycling computers."""
    point_lines: List[str] = []
    for segment in route.segments:
        for coordinate in segment.coordinates:
            description = xml_escape(
                f"{segment.name} ({segment.infrastructure}, "
                f"Safety {segment.safety_score:.0f}/100)"
            )
            point_lines.append(
                f'      <trkpt lat="{coordinate.latitude:.6f}" '
                f'lon="{coordinate.longitude:.6f}">'
                f"<desc>{description}</desc></trkpt>"
            )

    points_xml = "\n".join(point_lines)
    route_title = xml_escape(
        f"{route.route_type} Bicycle Route: {start_name} to {dest_name}"
    )
    meta_desc = xml_escape(
        f"Overall Safety Score: {route.overall_safety_score:.1f}/100 | "
        f"Distance: {route.total_distance_km:.1f} km | "
        f"Cycling Duration: {route.estimated_duration_mins:.0f} min"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="SafeCycle Drafter" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        "  <metadata>\n"
        f"    <name>{route_title}</name>\n"
        f"    <desc>{meta_desc}</desc>\n"
        f"    <time>{time.strftime('%Y-%m-%dT%H:%M:%SZ')}</time>\n"
        "  </metadata>\n"
        "  <trk>\n"
        f"    <name>{xml_escape(route.route_type)} Route</name>\n"
        "    <type>Cycling</type>\n"
        "    <trkseg>\n"
        f"{points_xml}\n"
        "    </trkseg>\n"
        "  </trk>\n"
        "</gpx>"
    )
