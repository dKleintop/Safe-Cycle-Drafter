"""main.py - SafeCycle: Safety-First Bike Route Planner (Python + Drafter).

Advanced technique notes (beyond introductory CS1):
- Uses the Drafter web framework (`@route`, `Page`, `Argument`, `Map`,
  `Download`, `SVG`, `Meter`) to render a 5-page interactive cycling safety
  planner in pure Python, plus Drafter's `add_website_js()` for street-following
  Leaflet polylines, labeled S/E pins, an animated bicycle loading screen,
  location autofill dropdowns, and a guard for Drafter v2.3.2's `<drafter-map>`
  unmount race condition.
- Uses `dataclasses.field(default_factory=list)` on `State` so each session
  holds its own independent `List[RouteSummary]` dataclass list.
- Uses `os.environ` and `sys.path` in `configure_runtime_environment()` to
  bootstrap local package resolution when launched locally.
- Imports `assert_equal` from `bakery` (with fallback to `drafter.assert_equal`
  inside Pyodide) so every route and helper function has unit tests.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def configure_runtime_environment() -> None:
    """Configure DRAFTER_ENTRY and local package path on local startup.

    Note: Cannot be unit tested cleanly in isolation because it mutates
    process-wide `os.environ` and `sys.path` at module import time.
    """
    current_file = globals().get("__file__") or "main.py"
    base_dir = os.path.dirname(os.path.abspath(current_file))
    try:
        os.environ["DRAFTER_ENTRY"] = os.path.abspath(current_file)
    except Exception:
        pass
    pkg_dir = os.path.join(base_dir, ".py311_packages")
    if os.path.exists(pkg_dir) and pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)


configure_runtime_environment()

try:  # noqa: E402
    from bakery import assert_equal  # type: ignore
except ImportError:
    from drafter import assert_equal  # noqa: E402

from drafter import (  # noqa: E402
    Argument,
    BulletedList,
    Button,
    CheckBox,
    Details,
    Div,
    Download,
    FooterContent,
    Header,
    HeaderContent,
    HorizontalRule,
    Label,
    Main,
    Map,
    MapMarker,
    Meter,
    Nav,
    Page,
    Paragraph,
    SVG,
    Section,
    SelectBox,
    SmallText,
    Strong,
    Table,
    Text,
    TextBox,
    TimeInput,
    add_website_css,
    add_website_header,
    add_website_js,
    hide_debug_information,
    route,
    set_site_information,
    set_website_framed,
    set_website_style,
    set_website_title,
    start_server,
)

from geocoding import (  # noqa: E402
    build_location_catalog_json,
    geocode_address,
)
from models import (  # noqa: E402
    Coordinate,
    RoadSegment,
    RouteOption,
    RouteSummary,
)
from routing import (  # noqa: E402
    compute_trip_schedule,
    format_distance,
    format_duration_text,
    parse_speed_mph,
    plan_bicycle_routes,
)
from safety import (  # noqa: E402
    DATA_SOURCES_METADATA,
    format_infrastructure_label,
    get_risk_label,
)
from storage import export_route_to_gpx  # noqa: E402
from styles import (  # noqa: E402
    DRAFTER_MAP_GUARD_JS,
    GOOGLE_FONTS_HEADER,
    SAFECYCLE_CSS,
)
from visuals import (  # noqa: E402
    build_map_polylines_json,
    build_safety_profile_svg,
    build_segment_polyline_json,
)

DEFAULT_START_COORD: Coordinate = Coordinate(39.676456, -75.747050)
DEFAULT_DEST_COORD: Coordinate = Coordinate(39.571807, -75.696079)
DEFAULT_START_LABEL: str = "Louis Redding Hall, Newark, DE"
DEFAULT_DEST_LABEL: str = "Kirkwood, DE"
VALID_ROUTE_MODES: Tuple[str, ...] = ("Safest", "Balanced", "Direct")
LOCATION_CATALOG_JSON: str = build_location_catalog_json()

RISK_CSS_CLASSES: Dict[str, str] = {
    "LOWER_RISK": "sc-risk-lower",
    "MODERATE": "sc-risk-moderate",
    "ELEVATED": "sc-risk-elevated",
    "HIGH_RISK": "sc-risk-high",
    "UNKNOWN": "sc-risk-unknown",
}

RISK_LEGEND_BANDS: Tuple[Tuple[str, str], ...] = (
    ("Selected Route", "#047857"),
    ("Alternative Route", "#64748b"),
)

CREDITS_AND_ATTRIBUTIONS: Tuple[Tuple[str, str, str], ...] = (
    (
        "OpenStreetMap Contributors",
        "Map tiles, street network, and bicycle infrastructure geometry.",
        "Open Database License (ODbL) · openstreetmap.org/copyright",
    ),
    (
        "Leaflet",
        "Interactive slippy maps, polylines, and custom S/E endpoint markers.",
        "BSD-2-Clause License · leafletjs.com",
    ),
    (
        "FOSSGIS / OSRM",
        "Live OpenStreetMap bicycle and vehicle street routing engine.",
        "BSD-2-Clause License · routing.openstreetmap.de",
    ),
    (
        "Photon by Komoot",
        "Live OpenStreetMap address geocoding and autofill search.",
        "Apache-2.0 / OSM Data · photon.komoot.io",
    ),
    (
        "Nominatim (OpenStreetMap)",
        "Open-source fallback geocoding service for street addresses.",
        "GPLv2 / OSM Data · nominatim.openstreetmap.org",
    ),
    (
        "Drafter Python Framework",
        "Pure-Python reactive web framework & Pyodide browser runtime.",
        "University of Delaware · drafter-edu.github.io/drafter",
    ),
    (
        "Google Fonts",
        "Plus Jakarta Sans, DM Sans, and JetBrains Mono typefaces.",
        "SIL Open Font License 1.1 · fonts.google.com",
    ),
    (
        "Public Crash & AADT Records",
        "State DOT and municipal Vision Zero bicycle safety benchmarks.",
        "Public Domain / Open Municipal Data (2022-2025)",
    ),
)

# Configure Drafter site metadata, custom CSS theme, and browser enhancements
set_site_information(
    author="SafeCycle Project (Python + Drafter)",
    description=(
        "SafeCycle is a safety-first bicycle route planner built with Python "
        "and Drafter. It builds real street-following OpenStreetMap bike "
        "routes and scores road segments from 0 to 100 using cycling "
        "infrastructure, speed limits, traffic exposure, crash history, and "
        "intersection risk so riders can compare Safest, Balanced, and Direct "
        "corridors, inspect segment evidence, and export GPX."
    ),
    sources=[
        "OpenStreetMap contributors (ODbL) & FOSSGIS OSRM bicycle routing",
        "Leaflet interactive maps & Photon / Nominatim geocoding",
        "Municipal Vision Zero & State DOT bicycle crash records (2022-2025)",
        "Drafter Python Web Framework (https://drafter-edu.github.io/drafter/)",
        "AI USE (chatgpt).txt",
        "chat_log.md",
        "AI_Explanation.md"
    ],
    planning=["CS1 Final Project Design Plan (1).docx"],
    links=["https://github.com/dKleintop/Safe-Cycle-Drafter"],
)
set_website_title("SafeCycle - Safety-First Bike Route Planner")
set_website_framed(False)
set_website_style("none")
hide_debug_information()
add_website_header(GOOGLE_FONTS_HEADER)
add_website_css(SAFECYCLE_CSS)
add_website_js(DRAFTER_MAP_GUARD_JS)


def install_browser_map_enhancer() -> None:
    """Activate browser UI enhancers and Leaflet overlay inside Pyodide.

    Note: Cannot be unit tested offline because the Pyodide `js` bridge module
    only exists inside the browser runtime; safely no-ops locally.
    """
    try:
        import js  # type: ignore

        js.eval(DRAFTER_MAP_GUARD_JS)
    except Exception:
        pass


install_browser_map_enhancer()


@dataclass
class State:
    """Persistent Drafter application state shared across all 5 pages."""

    current_page: str = "planner"
    start_address: str = DEFAULT_START_LABEL
    dest_address: str = DEFAULT_DEST_LABEL
    start_time: str = "08:30"
    planned_speed: float = 12.0
    preferred_mode: str = "Safest"
    max_risk_tolerance: str = "moderate"
    detour_tolerance: str = "50%"
    units: str = "mi"
    active_route_type: str = "Safest"
    selected_segment_id: str = ""
    route_summaries: List[RouteSummary] = field(default_factory=list)
    show_advanced: bool = False
    dark_mode: bool = False
    notification: str = ""
    error_message: str = ""


# ---------------------------------------------------------------------------
# Modular helper functions (pure Python + native Drafter components)
# ---------------------------------------------------------------------------


def is_remote_routing_enabled() -> bool:
    """Return True when live OpenStreetMap geocoding and OSRM are allowed."""
    return os.environ.get("DRAFTER_OFFLINE_TESTS", "").lower() not in (
        "1",
        "true",
        "yes",
    )


def get_risk_css_class(category: str) -> str:
    """Map a risk category string to its semantic SafeCycle CSS class."""
    return RISK_CSS_CLASSES.get(category, "sc-risk-unknown")


def get_score_css_class(score: float) -> str:
    """Map a numeric 0-100 safety score to a semantic CSS color class."""
    if score >= 80.0:
        return "sc-risk-lower"
    if score >= 60.0:
        return "sc-risk-moderate"
    return "sc-risk-high"


def get_score_risk_word(score: float) -> str:
    """Return a concise risk band summary string for a route score."""
    if score >= 80.0:
        return "Lower Risk"
    if score >= 60.0:
        return "Moderate Risk"
    if score >= 40.0:
        return "Elevated Risk"
    return "High Risk"


def get_score_bar_color(score: float) -> str:
    """Return a semantic hex color for the compact safety risk bar."""
    if score >= 80.0:
        return "#15803d"
    if score >= 60.0:
        return "#b45309"
    if score >= 40.0:
        return "#c2410c"
    return "#b91c1c"


def format_elevation_gain(elevation_m: float, units: str) -> str:
    """Format route elevation gain in feet (mi mode) or meters (km mode)."""
    safe_m = max(0.0, float(elevation_m))
    if units == "km":
        return f"+{safe_m:.0f} m"
    return f"+{safe_m * 3.28084:.0f} ft"


def describe_bike_infra(bike_infra_pct: float) -> str:
    """Return a short rider-facing description of bike infrastructure share."""
    if bike_infra_pct >= 60.0:
        return "Mostly dedicated bike paths, trails, or bike lanes"
    if bike_infra_pct >= 20.0:
        return "Mix of bikeways, paved shoulders, and calmer streets"
    if bike_infra_pct > 0.0:
        return "Limited dedicated bike lanes along this corridor"
    return "Shared roadway — no dedicated bike lane detected"


def get_nav_button_class(active_key: str, target_key: str) -> str:
    """Return top-bar navigation button CSS class for active highlight."""
    if active_key == target_key:
        return "sc-nav-btn sc-nav-active"
    return "sc-nav-btn"


def compute_midpoint(
    origin: Coordinate, destination: Coordinate
) -> Tuple[float, float]:
    """Return the geographic (lat, lon) midpoint between two Coordinates."""
    return (
        (origin.latitude + destination.latitude) / 2.0,
        (origin.longitude + destination.longitude) / 2.0,
    )


def sync_route_summaries(
    state: State, routes: Dict[str, RouteOption]
) -> List[RouteSummary]:
    """Store compact RouteSummary records for all generated corridors."""
    summaries: List[RouteSummary] = []
    for route_option in routes.values():
        summaries.append(
            RouteSummary(
                route_type=route_option.route_type,
                safety_score=round(route_option.overall_safety_score, 1),
                distance_km=round(route_option.total_distance_km, 2),
                duration_mins=round(route_option.estimated_duration_mins, 1),
                bike_infra_pct=round(
                    route_option.bike_infrastructure_percentage, 1
                ),
                high_risk_count=route_option.high_risk_segments_count,
            )
        )
    state.route_summaries = summaries
    return summaries


def compute_safety_gain_note(summaries: List[RouteSummary]) -> str:
    """Loop over RouteSummary records to summarize Safest vs Direct gain."""
    safest_score: Optional[float] = None
    direct_score: Optional[float] = None
    for summary in summaries:
        if summary.route_type == "Safest":
            safest_score = summary.safety_score
        elif summary.route_type == "Direct":
            direct_score = summary.safety_score
    if safest_score is not None and direct_score is not None:
        delta = safest_score - direct_score
        if delta > 0:
            return f"Safest +{delta:.0f} safety pts vs Direct"
    return f"{len(summaries)} corridors compared"


def build_help_tip(help_text: str) -> Div:
    """Render a circular '?' icon that reveals help_text on hover/focus."""
    return Div(
        Text("?"),
        Div(help_text, classes="sc-help-bubble"),
        classes="sc-help-tip",
        tabindex="0",
        aria_label=help_text,
    )


def build_card_header(
    title: str, help_text: str, level: int = 2
) -> Div:
    """Render a section heading with a top-right '?' hover help tooltip."""
    return Div(
        Header(title, level=level),
        build_help_tip(help_text),
        classes="sc-card-head-row",
    )


def resolve_endpoints(
    state: State, allow_remote: Optional[bool] = None
) -> Tuple[Optional[Coordinate], str, Optional[Coordinate], str, str]:
    """Geocode start and end addresses without running routing."""
    use_remote = (
        is_remote_routing_enabled() if allow_remote is None else allow_remote
    )
    start_coord, start_label = geocode_address(
        state.start_address, allow_remote=use_remote
    )
    if start_coord is None:
        return (None, state.start_address, None, state.dest_address, start_label)

    dest_coord, dest_label = geocode_address(
        state.dest_address, allow_remote=use_remote
    )
    if dest_coord is None:
        return (start_coord, start_label, None, state.dest_address, dest_label)

    return (start_coord, start_label, dest_coord, dest_label, "")


def resolve_corridor_routes(
    state: State, allow_remote: Optional[bool] = None
) -> Tuple[
    Optional[Coordinate],
    str,
    Optional[Coordinate],
    str,
    Dict[str, RouteOption],
    str,
]:
    """Geocode endpoints and generate Safest, Balanced, and Direct routes."""
    use_remote = (
        is_remote_routing_enabled() if allow_remote is None else allow_remote
    )
    start_coord, start_label, dest_coord, dest_label, err = resolve_endpoints(
        state, allow_remote=use_remote
    )
    if err or start_coord is None or dest_coord is None:
        return (start_coord, start_label, dest_coord, dest_label, {}, err)

    routes = plan_bicycle_routes(
        start_coord=start_coord,
        dest_coord=dest_coord,
        start_label=start_label,
        dest_label=dest_label,
        planned_speed_mph=state.planned_speed,
        start_time_24h=state.start_time,
        detour_tolerance=state.detour_tolerance,
        allow_remote=use_remote,
    )
    return (start_coord, start_label, dest_coord, dest_label, routes, "")


def get_active_route(
    state: State, routes: Dict[str, RouteOption]
) -> Optional[RouteOption]:
    """Return the currently selected RouteOption, or the safest available."""
    if not routes:
        return None
    if state.active_route_type in routes:
        return routes[state.active_route_type]
    return routes.get("Safest") or next(iter(routes.values()))


def build_endpoint_markers(
    start_coord: Coordinate,
    start_label: str,
    dest_coord: Coordinate,
    dest_label: str,
) -> List[MapMarker]:
    """Build only clean Start (S) and End (E) map endpoint pins."""
    return [
        MapMarker(
            start_coord.latitude,
            start_coord.longitude,
            f"Start (S): {start_label}",
        ),
        MapMarker(
            dest_coord.latitude,
            dest_coord.longitude,
            f"End (E): {dest_label}",
        ),
    ]


def build_map_legend_bar() -> Div:
    """Build a compact horizontal legend explaining route risk colors."""
    items: List[Any] = []
    for label, color in RISK_LEGEND_BANDS:
        items.append(
            Div(
                Text(
                    "",
                    classes="sc-legend-swatch",
                    style=f"background-color: {color};",
                ),
                Text(label),
                classes="sc-legend-item",
            )
        )
    return Div(*items, classes="sc-map-legend")


def build_topbar(active_key: str, dark_mode: bool = False) -> HeaderContent:
    """Build the 3-zone top bar with Moon/Sun dark toggle next to Settings."""
    theme_icon = "☀" if dark_mode else "☾"
    theme_title = "Switch to light mode" if dark_mode else "Switch to dark mode"
    return HeaderContent(
        Div(
            Button("SafeCycle", index, classes="sc-brand-btn"),
            Nav(
                Button(
                    "Planner",
                    index,
                    classes=get_nav_button_class(active_key, "planner"),
                ),
                Button(
                    "Results",
                    route_results_page,
                    classes=get_nav_button_class(active_key, "results"),
                ),
                Button(
                    "About",
                    about_page,
                    classes=get_nav_button_class(active_key, "about"),
                ),
                classes="sc-nav-links",
            ),
            Div(
                Button(
                    theme_icon,
                    handle_toggle_dark_mode,
                    classes="sc-theme-toggle",
                    title=theme_title,
                    aria_label=theme_title,
                ),
                Button(
                    "Settings",
                    settings_page,
                    classes=(
                        "sc-btn-primary sc-btn-sm"
                        if active_key == "settings"
                        else "sc-btn-sm"
                    ),
                ),
                classes="sc-topbar-actions",
            ),
            classes="sc-topbar-inner",
        ),
        classes="sc-topbar",
    )


def build_banners(state: State) -> List[Any]:
    """Consume and render one-shot notification or error feedback banners."""
    banners: List[Any] = []
    if state.notification:
        banners.append(Div(Text(state.notification), classes="sc-notice"))
        state.notification = ""
    if state.error_message:
        banners.append(Div(Text(state.error_message), classes="sc-danger-box"))
        state.error_message = ""
    return banners


def wrap_page_shell(
    state: State, active_key: str, body_items: List[Any]
) -> Page:
    """Wrap page content in the SafeCycle shell with topbar and footer."""
    shell_class = (
        "sc-app-shell sc-dark" if state.dark_mode else "sc-app-shell"
    )
    banners = build_banners(state)
    footer = FooterContent(
        Text(
            "SafeCycle prioritizes lower-risk cycling corridors using "
            "transparent evidence-based scoring. No route is guaranteed safe "
            "- always obey traffic laws and watch for road hazards."
        ),
        classes="sc-footer",
    )
    return Page(
        state,
        [
            Div(
                build_topbar(active_key, state.dark_mode),
                Main(*banners, *body_items, classes="sc-container"),
                footer,
                classes=shell_class,
            )
        ],
    )


def build_planner_form_section(state: State) -> Section:
    """Build the clean route planning form with location autofill inputs."""
    return Section(
        build_card_header(
            "Plan a Safer Bicycle Route",
            (
                "Safety first, speed second. Search any address, landmark, "
                "or lat/lon coordinates to compare real street-following "
                "Safest, Balanced, and Direct cycling routes."
            ),
            level=1,
        ),
        Div(
            Div(
                Div(
                    Label("Start Location", "start_address"),
                    TextBox(
                        "start_address",
                        state.start_address,
                        placeholder="Search an address, landmark, or lat, lon...",
                        autocomplete="off",
                        data_suggestions=LOCATION_CATALOG_JSON,
                    ),
                    classes="sc-field",
                ),
                Div(
                    Label("End Location", "dest_address"),
                    TextBox(
                        "dest_address",
                        state.dest_address,
                        placeholder="Search a destination address or landmark...",
                        autocomplete="off",
                        data_suggestions=LOCATION_CATALOG_JSON,
                    ),
                    classes="sc-field",
                ),
                classes="sc-endpoints-inputs",
            ),
            Button(
                "⇅",
                handle_swap_endpoints,
                classes="sc-swap-icon-btn",
                title="Swap Start & End",
                aria_label="Swap Start and End locations",
            ),
            classes="sc-endpoints-group",
        ),
        Div(
            Div(
                Label("Route Preference", "preferred_mode"),
                SelectBox(
                    "preferred_mode",
                    ["Safest", "Balanced", "Direct"],
                    default_value=state.preferred_mode,
                ),
            ),
            Div(
                Label("Max Risk Tolerance", "max_risk_tolerance"),
                SelectBox(
                    "max_risk_tolerance",
                    ["low", "moderate", "any"],
                    default_value=state.max_risk_tolerance,
                ),
            ),
            classes="sc-grid-2 sc-field",
        ),
        Div(
            Div(
                Label("Detour Tolerance", "detour_tolerance"),
                SelectBox(
                    "detour_tolerance",
                    ["15%", "35%", "50%", "100%"],
                    default_value=state.detour_tolerance,
                ),
            ),
            Div(
                Label("Departure Time", "start_time"),
                TimeInput("start_time", default_value=state.start_time),
            ),
            classes="sc-grid-2 sc-field",
        ),
        Div(
            Label("Planned Speed", "planned_speed"),
            TextBox(
                "planned_speed",
                f"{state.planned_speed:.1f}",
                placeholder="mph (e.g. 12.0)",
            ),
            classes="sc-field",
        ),
        Button(
            "Generate & Compare Safe Routes",
            handle_generate_route,
            classes="sc-btn-primary sc-btn-full",
        ),
        classes="sc-panel",
    )


def build_planner_map_section(
    center: Tuple[float, float], markers: List[MapMarker]
) -> Section:
    """Build the clean Trip Overview Map showing Start (S) and End (E) pins."""
    return Section(
        build_card_header(
            "Trip Overview Map",
            (
                "Green pin S marks your Start Location and red pin E marks "
                "your End Location. Pins update automatically when you pick "
                "or edit locations on the left."
            ),
            level=2,
        ),
        Map(
            "route_map",
            center=center,
            zoom=11,
            markers=markers,
            height=450,
        ),
        Details(
            "How SafeCycle Scores Routes & Risk Bands",
            BulletedList(
                [
                    "Lower Risk (80-100): Protected paths and greenways",
                    "Moderate Risk (60-79): Painted lanes and shoulders",
                    "Elevated Risk (40-59): Shared lanes or 30-35 mph roads",
                    "High Risk (<40): Multi-lane arterials, 40+ mph speeds",
                    "Insufficient Data: Missing records treated cautiously",
                ]
            ),
        ),
        classes="sc-panel",
    )


def build_results_map_column(
    routes: Dict[str, RouteOption],
    active_route: RouteOption,
    start_coord: Coordinate,
    start_label: str,
    dest_coord: Coordinate,
    dest_label: str,
) -> Section:
    """Build the left Results column with clickable routes on the map."""
    polylines_json = build_map_polylines_json(routes, active_route.route_type)
    endpoint_markers = build_endpoint_markers(
        start_coord, start_label, dest_coord, dest_label
    )
    return Section(
        Div(
            build_map_legend_bar(),
            build_help_tip(
                "All distinct routes (up to top 3) are marked on the map. "
                "Click any route line or badge to select it and view its "
                "details on the right."
            ),
            classes="sc-map-toolbar",
        ),
        Map(
            "results_map",
            center=compute_midpoint(start_coord, dest_coord),
            zoom=12,
            markers=endpoint_markers,
            height=460,
            data_polylines=polylines_json,
        ),
        classes="sc-panel sc-panel-compact",
    )


def build_selected_route_column(
    routes: Dict[str, RouteOption],
    active_route: RouteOption,
    start_label: str,
    dest_label: str,
    state: State,
) -> Section:
    """Build the clean Basic Route Overview panel for the selected route."""
    tab_buttons: List[Any] = []
    for route_option in routes.values():
        is_active = route_option.route_type == active_route.route_type
        tab_cls = (
            "sc-route-tab sc-route-tab-active" if is_active else "sc-route-tab"
        )
        tab_buttons.append(
            Button(
                f"{route_option.route_type} ({route_option.overall_safety_score:.0f})",
                select_route_mode,
                Argument("route_type", route_option.route_type),
                classes=tab_cls,
                data_route_mode=route_option.route_type,
            )
        )

    depart_str, arrival_str = compute_trip_schedule(
        state.start_time, active_route.estimated_duration_mins
    )
    score_val = max(0.0, min(100.0, active_route.overall_safety_score))
    risk_word = get_score_risk_word(score_val)
    risk_cls = get_score_css_class(score_val)
    bar_color = get_score_bar_color(score_val)
    bar_pct = max(8.0, score_val)
    infra_pct = max(
        0.0, min(100.0, active_route.bike_infrastructure_percentage)
    )
    gpx_xml = export_route_to_gpx(active_route, start_label, dest_label)
    safe_slug = active_route.route_type.lower()
    adv_label = "Hide Advanced" if state.show_advanced else "Advanced Details"

    return Section(
        Div(*tab_buttons, classes="sc-route-tabs"),
        Div(
            Div(
                Div(
                    Header(f"{active_route.route_type} Route", level=2),
                    SmallText(
                        f"{depart_str} – {arrival_str}",
                        classes="sc-mono sc-meta-line",
                    ),
                ),
                Div(
                    Div(f"{score_val:.0f}/100", classes="sc-kpi-value"),
                    SmallText(risk_word, classes=risk_cls),
                    Div(
                        Div(
                            "",
                            classes="sc-score-bar-fill",
                            style=(
                                f"width: {bar_pct:.0f}%; "
                                f"background-color: {bar_color};"
                            ),
                        ),
                        classes="sc-score-bar-track",
                    ),
                    classes="sc-route-card-score",
                ),
                classes="sc-route-card-head",
            ),
            Div(
                Div(
                    Text(
                        format_distance(
                            active_route.total_distance_km, state.units
                        ),
                        classes="sc-trip-stat-val",
                    ),
                    Text("Distance", classes="sc-trip-stat-lbl"),
                    classes="sc-trip-stat",
                ),
                Div(
                    Text(
                        format_duration_text(
                            active_route.estimated_duration_mins
                        ),
                        classes="sc-trip-stat-val",
                    ),
                    Text("Est. Time", classes="sc-trip-stat-lbl"),
                    classes="sc-trip-stat",
                ),
                Div(
                    Text(
                        format_elevation_gain(
                            active_route.elevation_gain_m, state.units
                        ),
                        classes="sc-trip-stat-val",
                    ),
                    Text("Elevation", classes="sc-trip-stat-lbl"),
                    classes="sc-trip-stat",
                ),
                classes="sc-trip-stats-grid",
            ),
            Div(
                Div(
                    Text("Bike Infrastructure", classes="sc-infra-title"),
                    Text(f"{infra_pct:.0f}%", classes="sc-infra-pct"),
                    classes="sc-infra-head",
                ),
                Div(
                    Div(
                        "",
                        classes="sc-infra-fill",
                        style=f"width: {infra_pct:.0f}%;",
                    ),
                    classes="sc-infra-track",
                ),
                Text(
                    describe_bike_infra(infra_pct), classes="sc-infra-sub"
                ),
                classes="sc-infra-highlight",
            ),
            Div(
                Download(
                    "Download GPX",
                    f"safecycle_{safe_slug}_route.gpx",
                    gpx_xml,
                    content_type="application/gpx+xml",
                    classes="sc-btn sc-btn-primary sc-btn-sm",
                ),
                Button("Edit Trip", index, classes="sc-btn-sm"),
                Button(
                    adv_label,
                    handle_toggle_advanced,
                    classes="sc-btn-sm",
                ),
                classes="sc-route-actions",
            ),
            classes="sc-selected-route-box",
        ),
        classes="sc-panel sc-panel-compact",
    )


def build_advanced_route_notes_section(
    active_route: RouteOption, summaries: List[RouteSummary]
) -> Section:
    """Build the Advanced Safety Cautions and risk-exposure summary section."""
    gain_note = compute_safety_gain_note(summaries)
    warning_blocks: List[Any] = []
    if active_route.warnings:
        warning_blocks.append(
            Div(
                Strong("Safety Cautions"),
                BulletedList(active_route.warnings),
                classes="sc-compact-warnings",
            )
        )
    return Section(
        build_card_header(
            f"Safety Cautions & Risk Summary ({active_route.route_type})",
            (
                "Detailed exposure counts, corridor rationale, and road "
                "cautions for riders inspecting advanced safety data."
            ),
            level=2,
        ),
        Div(
            Div(
                Text(
                    str(active_route.high_risk_segments_count),
                    classes="sc-route-metric-val",
                ),
                Text("High Risk Segs", classes="sc-route-metric-lbl"),
                classes="sc-route-metric-item",
            ),
            Div(
                Text(
                    str(active_route.major_intersections_count),
                    classes="sc-route-metric-val",
                ),
                Text("Major Junctions", classes="sc-route-metric-lbl"),
                classes="sc-route-metric-item",
            ),
            Div(
                Text(
                    active_route.confidence_level,
                    classes="sc-route-metric-val",
                ),
                Text("Data Confidence", classes="sc-route-metric-lbl"),
                classes="sc-route-metric-item",
            ),
            classes="sc-route-metrics",
        ),
        Paragraph(
            active_route.selection_rationale,
            classes="sc-route-rationale",
            style="margin-top: 10px;",
        ),
        SmallText(gain_note, classes="sc-meta-line"),
        *warning_blocks,
        classes="sc-panel",
    )


def build_safety_spectrum_section(
    active_route: RouteOption, dark_mode: bool
) -> Section:
    """Build the Advanced Segment Safety Spectrum SVG section."""
    svg_profile = build_safety_profile_svg(
        active_route, width=1120, height=155, dark_mode=dark_mode
    )
    return Section(
        build_card_header(
            f"Segment Safety Spectrum ({active_route.route_type})",
            (
                "Each bar represents one street or trail segment sized by "
                "distance and colored by its 0-100 objective safety score."
            ),
            level=2,
        ),
        SVG(svg_profile, width=1120, height=155, viewBox="0 0 1120 155"),
        classes="sc-panel",
    )


def build_segment_breakdown_section(active_route: RouteOption) -> Section:
    """Build the road segment safety table with Inspect buttons."""
    segment_rows: List[List[Any]] = []
    for index_num, segment in enumerate(active_route.segments, start=1):
        speed_text = (
            f"{segment.speed_limit_mph} mph"
            if segment.speed_limit_mph is not None
            else "Unknown"
        )
        score_cls = f"sc-mono {get_risk_css_class(segment.risk_category)}"
        segment_rows.append(
            [
                Strong(segment.name),
                Text(format_infrastructure_label(segment.infrastructure)),
                Text(speed_text, classes="sc-mono"),
                Text(f"{segment.safety_score:.0f} / 100", classes=score_cls),
                Text(
                    f"{get_risk_label(segment.risk_category)} "
                    f"({segment.confidence})"
                ),
                Button(
                    f"Inspect #{index_num}",
                    inspect_segment,
                    Argument("segment_id", segment.segment_id),
                    classes="sc-btn-sm",
                ),
            ]
        )
    return Section(
        build_card_header(
            f"Road Segment Breakdown ({active_route.route_type})",
            (
                "Every road segment is scored transparently from 0 to 100. "
                "Click Inspect on any segment to view street geometry and "
                "detailed risk evidence."
            ),
            level=2,
        ),
        Table(
            segment_rows,
            header=[
                "Road / Trail Segment",
                "Cycling Infrastructure",
                "Speed Limit",
                "Safety Score",
                "Risk & Confidence",
                "Evidence",
            ],
        ),
        classes="sc-panel",
    )


def build_advanced_diagnostics_section(
    routes: Dict[str, RouteOption], units: str
) -> Section:
    """Build the advanced multi-corridor diagnostics comparison table."""
    diag_rows: List[List[Any]] = [
        [
            route_option.route_type,
            f"{route_option.overall_safety_score:.1f} / 100",
            format_distance(route_option.total_distance_km, units),
            format_duration_text(route_option.estimated_duration_mins),
            f"{route_option.bike_infrastructure_percentage:.0f}%",
            str(route_option.high_risk_segments_count),
            str(route_option.major_intersections_count),
            route_option.confidence_level,
        ]
        for route_option in routes.values()
    ]
    return Section(
        Header("Advanced Corridor Diagnostics", level=3),
        Table(
            diag_rows,
            header=[
                "Mode",
                "Safety",
                "Distance",
                "Est. Time",
                "Bike Infra %",
                "High Risk Segs",
                "Major Junctions",
                "Confidence",
            ],
        ),
        classes="sc-panel",
    )


def render_results_view(
    state: State,
    start_coord: Coordinate,
    start_label: str,
    dest_coord: Coordinate,
    dest_label: str,
    routes: Dict[str, RouteOption],
) -> Page:
    """Render compact split Results view with optional Advanced Detail View."""
    state.current_page = "results"
    sync_route_summaries(state, routes)
    active_route = get_active_route(state, routes)
    assert active_route is not None
    state.active_route_type = active_route.route_type

    map_column = build_results_map_column(
        routes,
        active_route,
        start_coord,
        start_label,
        dest_coord,
        dest_label,
    )
    route_column = build_selected_route_column(
        routes, active_route, start_label, dest_label, state
    )

    advanced_blocks: List[Any] = []
    if state.show_advanced:
        advanced_blocks.append(
            build_advanced_route_notes_section(
                active_route, state.route_summaries
            )
        )
        advanced_blocks.append(
            build_safety_spectrum_section(active_route, state.dark_mode)
        )
        advanced_blocks.append(build_segment_breakdown_section(active_route))
        advanced_blocks.append(
            build_advanced_diagnostics_section(routes, state.units)
        )

    return wrap_page_shell(
        state,
        "results",
        [
            Div(map_column, route_column, classes="sc-results-split"),
            *advanced_blocks,
        ],
    )


def find_selected_segment(
    active_route: RouteOption, selected_id: str
) -> Optional[RoadSegment]:
    """Locate the selected RoadSegment by ID, defaulting to the first."""
    for segment in active_route.segments:
        if segment.segment_id == selected_id:
            return segment
    return active_route.segments[0] if active_route.segments else None


def build_segment_kpi_strip(segment: RoadSegment, units: str) -> Div:
    """Build the 4-card KPI strip for the Segment Safety Details page."""
    speed_display = (
        f"{segment.speed_limit_mph} mph"
        if segment.speed_limit_mph is not None
        else "Unknown"
    )
    return Div(
        Div(
            Div(
                format_infrastructure_label(segment.infrastructure),
                classes="sc-kpi-value",
                style="font-size: 1.05rem;",
            ),
            Div("Infrastructure Class", classes="sc-kpi-label"),
            classes="sc-panel",
        ),
        Div(
            Div(speed_display, classes="sc-kpi-value"),
            Div("Posted Speed Limit", classes="sc-kpi-label"),
            classes="sc-panel",
        ),
        Div(
            Div(
                segment.traffic_exposure.replace("_", " ").title(),
                classes="sc-kpi-value",
                style="font-size: 1.15rem;",
            ),
            Div("Traffic Exposure", classes="sc-kpi-label"),
            classes="sc-panel",
        ),
        Div(
            Div(
                format_distance(segment.length_km, units),
                classes="sc-kpi-value",
            ),
            Div("Segment Length", classes="sc-kpi-label"),
            classes="sc-panel",
        ),
        classes="sc-grid-4",
    )


def build_methodology_table() -> Table:
    """Build the weighted scoring methodology reference table."""
    return Table(
        [
            [
                "Cycling Infrastructure",
                "30%",
                "Protected bike paths (100) vs unprotected arterials (15).",
            ],
            [
                "Posted Speed Limit",
                "20%",
                "<=20 mph (90-100) vs 40+ mph high-fatality zones (10).",
            ],
            [
                "Historical Crash Record",
                "20%",
                "Reported bicycle crashes weighted by severe/fatal outcomes.",
            ],
            [
                "Traffic Exposure (AADT)",
                "15%",
                "Quiet residential/trail corridors vs heavy truck arterials.",
            ],
            [
                "Intersection Conflict",
                "15%",
                "Protected crossings vs multi-lane high-speed merge ramps.",
            ],
        ],
        header=["Scoring Factor", "Weight", "Transparent Rule"],
    )


def build_credits_section() -> Section:
    """Build the Credits & Attributions section for all data and libraries."""
    credit_rows = [
        [Strong(name), role, license_text]
        for name, role, license_text in CREDITS_AND_ATTRIBUTIONS
    ]
    return Section(
        build_card_header(
            "Credits & Open-Source Attributions",
            (
                "SafeCycle relies on open geographic data, routing engines, "
                "and open-source software libraries credited below."
            ),
            level=2,
        ),
        Table(
            credit_rows,
            header=["Service / Library", "Role in SafeCycle", "Credit / License"],
        ),
        classes="sc-panel",
    )


# ---------------------------------------------------------------------------
# PAGE 1: Route Planner (index)
# ---------------------------------------------------------------------------


@route
def index(state: State) -> Page:
    """Home page: Clean trip planner with autofill and endpoint overview."""
    state.current_page = "planner"
    start_coord, start_label, dest_coord, dest_label, _ = resolve_endpoints(
        state, allow_remote=False
    )
    if (
        (start_coord is None or dest_coord is None)
        and is_remote_routing_enabled()
    ):
        start_coord, start_label, dest_coord, dest_label, _ = resolve_endpoints(
            state, allow_remote=True
        )
    origin = start_coord or DEFAULT_START_COORD
    destination = dest_coord or DEFAULT_DEST_COORD
    origin_text = start_label if start_coord else DEFAULT_START_LABEL
    dest_text = dest_label if dest_coord else DEFAULT_DEST_LABEL

    planner_form = build_planner_form_section(state)
    map_panel = build_planner_map_section(
        compute_midpoint(origin, destination),
        build_endpoint_markers(origin, origin_text, destination, dest_text),
    )
    return wrap_page_shell(
        state,
        "planner",
        [Div(planner_form, map_panel, classes="sc-split-2")],
    )


@route
def handle_generate_route(
    state: State,
    start_address: str = "",
    dest_address: str = "",
    preferred_mode: str = "Safest",
    max_risk_tolerance: str = "moderate",
    detour_tolerance: str = "50%",
    start_time: str = "08:30",
    planned_speed: str = "12.0",
) -> Page:
    """Validate trip inputs, update State, and render Route Comparison."""
    state.start_address = start_address.strip() or state.start_address
    state.dest_address = dest_address.strip() or state.dest_address
    state.preferred_mode = (
        preferred_mode if preferred_mode in VALID_ROUTE_MODES else "Safest"
    )
    state.active_route_type = state.preferred_mode
    state.max_risk_tolerance = max_risk_tolerance or "moderate"
    state.detour_tolerance = detour_tolerance or "50%"
    state.start_time = start_time.strip() or "08:30"
    state.planned_speed = parse_speed_mph(planned_speed, state.planned_speed)

    start_coord, start_label, dest_coord, dest_label, routes, error_text = (
        resolve_corridor_routes(state)
    )
    if error_text or not routes or start_coord is None or dest_coord is None:
        state.error_message = error_text or "Unable to resolve addresses."
        return index(state)

    return render_results_view(
        state, start_coord, start_label, dest_coord, dest_label, routes
    )


@route
def handle_swap_endpoints(
    state: State,
    start_address: str = "",
    dest_address: str = "",
) -> Page:
    """Swap the current Start and End addresses, preserving unsaved edits."""
    current_start = start_address.strip() or state.start_address
    current_dest = dest_address.strip() or state.dest_address
    state.start_address = current_dest
    state.dest_address = current_start
    state.notification = "Swapped start and end locations."
    return index(state)


@route
def handle_toggle_dark_mode(state: State) -> Page:
    """Toggle dark mode from the top-bar Moon/Sun icon and refresh view."""
    state.dark_mode = not state.dark_mode
    if state.current_page == "results":
        return route_results_page(state)
    if state.current_page == "segment":
        return segment_details_page(state)
    if state.current_page == "settings":
        return settings_page(state)
    if state.current_page == "about":
        return about_page(state)
    return index(state)


# ---------------------------------------------------------------------------
# PAGE 2: Route Comparison & Results
# ---------------------------------------------------------------------------


@route
def route_results_page(state: State) -> Page:
    """Results page: Compare Safest, Balanced, and Direct street corridors."""
    start_coord, start_label, dest_coord, dest_label, routes, err = (
        resolve_corridor_routes(state)
    )
    if err or not routes or start_coord is None or dest_coord is None:
        state.error_message = err or "No route available for these endpoints."
        return index(state)

    return render_results_view(
        state, start_coord, start_label, dest_coord, dest_label, routes
    )


@route
def select_route_mode(state: State, route_type: str) -> Page:
    """Switch active corridor selection between available route options."""
    if route_type in VALID_ROUTE_MODES:
        state.active_route_type = route_type
    return route_results_page(state)


@route
def handle_toggle_advanced(state: State) -> Page:
    """Toggle Advanced Detail View (Safety Spectrum & Segment Breakdown)."""
    state.show_advanced = not state.show_advanced
    return route_results_page(state)


@route
def inspect_segment(state: State, segment_id: str) -> Page:
    """Open the Segment Safety Evidence page for the chosen road segment."""
    state.selected_segment_id = segment_id
    return segment_details_page(state)


# ---------------------------------------------------------------------------
# PAGE 3: Segment Safety Details & Evidence
# ---------------------------------------------------------------------------


@route
def segment_details_page(state: State) -> Page:
    """Segment Details page: Street polyline map and full evidence factors."""
    state.current_page = "segment"
    _, _, _, _, routes, _ = resolve_corridor_routes(state)
    active_route = get_active_route(state, routes)
    if active_route is None or not active_route.segments:
        state.error_message = "Generate a route first to inspect segments."
        return index(state)

    selected = find_selected_segment(active_route, state.selected_segment_id)
    assert selected is not None
    state.selected_segment_id = selected.segment_id

    mid_coord = selected.coordinates[len(selected.coordinates) // 2]
    start_pt = selected.coordinates[0]
    end_pt = selected.coordinates[-1]
    segment_markers = [
        MapMarker(
            start_pt.latitude,
            start_pt.longitude,
            f"Start of segment: {selected.name}",
        ),
        MapMarker(
            end_pt.latitude,
            end_pt.longitude,
            f"End of segment: {selected.name}",
        ),
    ]
    segment_polyline_json = build_segment_polyline_json(selected)

    if selected.crash_record is not None:
        crash_summary = (
            f"Total bicycle crashes ({selected.crash_record.date_range}): "
            f"{selected.crash_record.total_crashes} | Severe injuries: "
            f"{selected.crash_record.severe_injuries} | Fatalities: "
            f"{selected.crash_record.fatalities}"
        )
        crash_limitations = selected.crash_record.limitations
    else:
        crash_summary = (
            "No verified municipal crash ledger available for this segment."
        )
        crash_limitations = (
            "Missing collision data does not mean a road is safe; confidence "
            "is reduced accordingly."
        )

    alternative_blocks: List[Any] = []
    if selected.safer_alternative:
        alternative_blocks.append(
            Div(
                Strong("Recommended Safer Alternative: "),
                Text(selected.safer_alternative),
                classes="sc-notice",
            )
        )

    kpi_strip = build_segment_kpi_strip(selected, state.units)
    evidence_split = Div(
        Section(
            Header("Positive Safety Factors", level=3),
            BulletedList(
                selected.positive_factors
                or ["No major protective factors recorded on this segment."]
            ),
            classes="sc-panel",
        ),
        Section(
            Header("Risk Factors & Caution Flags", level=3),
            BulletedList(
                selected.negative_factors
                or ["No major elevated hazard flags recorded."]
            ),
            classes="sc-panel",
        ),
        classes="sc-grid-2",
    )

    return wrap_page_shell(
        state,
        "results",
        [
            Section(
                SmallText(
                    f"SEGMENT SAFETY EVIDENCE · "
                    f"{active_route.route_type.upper()} CORRIDOR",
                    classes="sc-mono sc-meta-line",
                ),
                Header(selected.name, level=1),
                Div(
                    Text(
                        f"Safety Score: {selected.safety_score:.0f} / 100 · "
                        f"{get_risk_label(selected.risk_category)} · "
                        f"Confidence: {selected.confidence}",
                        classes=get_risk_css_class(selected.risk_category),
                    ),
                    classes="sc-field",
                ),
                Meter(
                    selected.safety_score,
                    min=0,
                    max=100,
                    low=40,
                    high=80,
                    optimum=90,
                ),
                SmallText(selected.evidence_notes, classes="sc-meta-line"),
                classes="sc-panel",
            ),
            kpi_strip,
            *alternative_blocks,
            evidence_split,
            Section(
                Header("Collision History & Street Map", level=3),
                Paragraph(crash_summary),
                SmallText(crash_limitations, classes="sc-meta-line"),
                HorizontalRule(),
                Map(
                    "segment_map",
                    center=(mid_coord.latitude, mid_coord.longitude),
                    zoom=14,
                    markers=segment_markers,
                    height=340,
                    data_polylines=segment_polyline_json,
                ),
                Div(
                    Button(
                        "Back to Route Comparison",
                        route_results_page,
                        classes="sc-btn-primary",
                    ),
                    classes="sc-btn-row",
                    style="margin-top: 16px;",
                ),
                classes="sc-panel",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# PAGE 4: Rider Preferences & Settings
# ---------------------------------------------------------------------------


@route
def settings_page(state: State) -> Page:
    """Settings page: Configure planned speed, units, diagnostics, theme."""
    state.current_page = "settings"
    return wrap_page_shell(
        state,
        "settings",
        [
            Section(
                build_card_header(
                    "Rider Preferences & Map Settings",
                    (
                        "Customize default planned speed, distance units, "
                        "preferred route mode, diagnostics, and light or "
                        "dark theme."
                    ),
                    level=1,
                ),
                Div(
                    Div(
                        Label("Default Planned Speed", "planned_speed"),
                        TextBox(
                            "planned_speed",
                            f"{state.planned_speed:.1f}",
                            placeholder="mph (5-28)",
                        ),
                    ),
                    Div(
                        Label("Default Departure Time", "start_time"),
                        TimeInput(
                            "start_time", default_value=state.start_time
                        ),
                    ),
                    classes="sc-grid-2 sc-field",
                ),
                Div(
                    Div(
                        Label("Default Route Mode", "preferred_mode"),
                        SelectBox(
                            "preferred_mode",
                            ["Safest", "Balanced", "Direct"],
                            default_value=state.preferred_mode,
                        ),
                    ),
                    Div(
                        Label("Distance Units", "units"),
                        SelectBox(
                            "units",
                            ["mi", "km"],
                            default_value=state.units,
                        ),
                    ),
                    classes="sc-grid-2 sc-field",
                ),
                Div(
                    CheckBox("show_advanced", default_value=state.show_advanced),
                    Label(
                        "Show Advanced Detail View (Safety Spectrum, "
                        "Segment Breakdown & Diagnostics)",
                        "show_advanced",
                    ),
                    classes="sc-check-row",
                ),
                Div(
                    CheckBox("dark_mode", default_value=state.dark_mode),
                    Label(
                        "Enable Dark Map & Interface Theme",
                        "dark_mode",
                    ),
                    classes="sc-check-row",
                ),
                Div(
                    Button(
                        "Save Preferences",
                        handle_save_settings,
                        classes="sc-btn-primary",
                    ),
                    Button("Back to Planner", index),
                    classes="sc-btn-row",
                    style="margin-top: 16px;",
                ),
                classes="sc-panel",
            )
        ],
    )


@route
def handle_save_settings(
    state: State,
    planned_speed: str = "12.0",
    start_time: str = "08:30",
    preferred_mode: str = "Safest",
    units: str = "mi",
    show_advanced: bool = False,
    dark_mode: bool = False,
) -> Page:
    """Persist updated rider preferences into State and return to Planner."""
    state.planned_speed = parse_speed_mph(planned_speed, state.planned_speed)
    state.start_time = start_time.strip() or state.start_time
    if preferred_mode in VALID_ROUTE_MODES:
        state.preferred_mode = preferred_mode
        state.active_route_type = preferred_mode
    state.units = "km" if units == "km" else "mi"
    state.show_advanced = bool(show_advanced)
    state.dark_mode = bool(dark_mode)
    state.notification = (
        f"Preferences updated: {state.planned_speed:.1f} mph, "
        f"{state.units.upper()}, {state.preferred_mode} mode."
    )
    return index(state)


# ---------------------------------------------------------------------------
# PAGE 5: Safety Methodology, Data Sources & Credits
# ---------------------------------------------------------------------------


@route
def about_page(state: State) -> Page:
    """About page: Scoring methodology, data sources, and attributions."""
    state.current_page = "about"
    source_rows = [
        [source["name"], source["coverage"], source["limitations"]]
        for source in DATA_SOURCES_METADATA.values()
    ]
    return wrap_page_shell(
        state,
        "about",
        [
            Section(
                build_card_header(
                    "How SafeCycle Evaluates Cycling Safety",
                    (
                        "SafeCycle combines OpenStreetMap street routing with "
                        "transparent multi-factor safety scoring instead of "
                        "optimizing solely for vehicle travel time."
                    ),
                    level=1,
                ),
                build_methodology_table(),
                classes="sc-panel",
            ),
            Section(
                build_card_header(
                    "Data Sources & Limitations",
                    (
                        "Coverage and honest data caveats behind SafeCycle's "
                        "route scoring model."
                    ),
                    level=2,
                ),
                Table(
                    source_rows,
                    header=["Data Source", "Coverage", "Known Limitations"],
                ),
                classes="sc-panel",
            ),
            build_credits_section(),
        ],
    )


# ---------------------------------------------------------------------------
# Built-in bakery assert_equal unit tests for every helper and @route
# ---------------------------------------------------------------------------


def run_bakery_unit_tests() -> None:
    """Run bakery assert_equal unit tests for every helper and @route.

    Note: This is the test runner function itself; it forces offline mode
    while testing all routes and helpers so assertions remain deterministic.
    """
    prev_offline = os.environ.get("DRAFTER_OFFLINE_TESTS")
    os.environ["DRAFTER_OFFLINE_TESTS"] = "1"
    try:
        assert_equal(is_remote_routing_enabled(), False)
        assert_equal(get_risk_css_class("LOWER_RISK"), "sc-risk-lower")
        assert_equal(get_risk_css_class("UNKNOWN"), "sc-risk-unknown")
        assert_equal(get_score_css_class(88.0), "sc-risk-lower")
        assert_equal(get_score_css_class(65.0), "sc-risk-moderate")
        assert_equal(get_score_css_class(32.0), "sc-risk-high")
        assert_equal(get_score_risk_word(85.0), "Lower Risk")
        assert_equal(get_score_risk_word(70.0), "Moderate Risk")
        assert_equal(get_score_risk_word(50.0), "Elevated Risk")
        assert_equal(get_score_risk_word(25.0), "High Risk")
        assert_equal(get_score_bar_color(85.0), "#15803d")
        assert_equal(get_score_bar_color(65.0), "#b45309")
        assert_equal(get_score_bar_color(50.0), "#c2410c")
        assert_equal(get_score_bar_color(20.0), "#b91c1c")
        assert_equal(format_elevation_gain(100.0, "km"), "+100 m")
        assert_equal(format_elevation_gain(100.0, "mi"), "+328 ft")
        assert_equal("dedicated" in describe_bike_infra(75.0).lower(), True)
        assert_equal("shared" in describe_bike_infra(0.0).lower(), True)
        assert_equal(
            get_nav_button_class("planner", "planner"),
            "sc-nav-btn sc-nav-active",
        )
        assert_equal(get_nav_button_class("planner", "about"), "sc-nav-btn")
        assert_equal(
            compute_midpoint(Coordinate(10.0, 20.0), Coordinate(20.0, 40.0)),
            (15.0, 30.0),
        )
        assert_equal(
            isinstance(build_help_tip("Help info"), Div), True
        )
        assert_equal(
            isinstance(build_card_header("Title", "Help info", level=2), Div),
            True,
        )

        test_state = State()
        sc, sl, dc, dl, ep_err = resolve_endpoints(test_state, False)
        assert_equal(ep_err, "")
        assert_equal(sc is not None and dc is not None, True)

        start_c, s_lbl, dest_c, d_lbl, routes, err = resolve_corridor_routes(
            test_state, allow_remote=False
        )
        assert_equal(err, "")
        assert_equal(start_c is not None and dest_c is not None, True)
        assert_equal(len(routes), 3)

        summaries = sync_route_summaries(test_state, routes)
        assert_equal(len(summaries), 3)
        assert_equal(len(test_state.route_summaries), 3)
        gain_note = compute_safety_gain_note(summaries)
        assert_equal("Safest +" in gain_note, True)

        active = get_active_route(test_state, routes)
        assert_equal(active is not None, True)
        assert active is not None and start_c is not None and dest_c is not None
        assert_equal(active.route_type, "Safest")

        markers = build_endpoint_markers(start_c, s_lbl, dest_c, d_lbl)
        assert_equal(len(markers), 2)
        assert_equal(isinstance(build_map_legend_bar(), Div), True)
        assert_equal(
            isinstance(build_topbar("planner", False), HeaderContent), True
        )
        assert_equal(
            isinstance(build_topbar("results", True), HeaderContent), True
        )

        test_state.notification = "Hello"
        test_state.error_message = "Warn"
        banners = build_banners(test_state)
        assert_equal(len(banners), 2)
        assert_equal(test_state.notification, "")
        assert_equal(test_state.error_message, "")

        wrapped = wrap_page_shell(test_state, "planner", [Paragraph("Body")])
        assert_equal(isinstance(wrapped, Page), True)
        assert_equal(
            isinstance(build_planner_form_section(test_state), Section), True
        )
        assert_equal(
            isinstance(
                build_planner_map_section((39.6, -75.7), markers), Section
            ),
            True,
        )
        assert_equal(
            isinstance(
                build_results_map_column(
                    routes, active, start_c, s_lbl, dest_c, d_lbl
                ),
                Section,
            ),
            True,
        )
        assert_equal(
            isinstance(
                build_selected_route_column(
                    routes, active, s_lbl, d_lbl, test_state
                ),
                Section,
            ),
            True,
        )
        assert_equal(
            isinstance(
                build_advanced_route_notes_section(active, summaries), Section
            ),
            True,
        )
        assert_equal(
            isinstance(build_safety_spectrum_section(active, False), Section),
            True,
        )
        assert_equal(
            isinstance(build_segment_breakdown_section(active), Section), True
        )
        assert_equal(
            isinstance(
                build_advanced_diagnostics_section(routes, "mi"), Section
            ),
            True,
        )
        assert_equal(
            isinstance(
                render_results_view(
                    test_state, start_c, s_lbl, dest_c, d_lbl, routes
                ),
                Page,
            ),
            True,
        )

        found_seg = find_selected_segment(active, active.segments[0].segment_id)
        assert_equal(found_seg is not None, True)
        assert found_seg is not None
        assert_equal(found_seg.segment_id, active.segments[0].segment_id)
        assert_equal(
            isinstance(build_segment_kpi_strip(found_seg, "mi"), Div), True
        )
        assert_equal(isinstance(build_methodology_table(), Table), True)
        assert_equal(isinstance(build_credits_section(), Section), True)

        # All 5 Page @routes
        assert_equal(isinstance(index(test_state), Page), True)
        assert_equal(test_state.current_page, "planner")
        assert_equal(isinstance(route_results_page(test_state), Page), True)
        assert_equal(test_state.current_page, "results")
        assert_equal(isinstance(segment_details_page(test_state), Page), True)
        assert_equal(test_state.current_page, "segment")
        assert_equal(isinstance(settings_page(test_state), Page), True)
        assert_equal(test_state.current_page, "settings")
        assert_equal(isinstance(about_page(test_state), Page), True)
        assert_equal(test_state.current_page, "about")

        # All action @routes
        assert_equal(
            isinstance(
                handle_generate_route(
                    test_state,
                    start_address=DEFAULT_START_LABEL,
                    dest_address=DEFAULT_DEST_LABEL,
                    preferred_mode="Balanced",
                    planned_speed="14.0",
                ),
                Page,
            ),
            True,
        )
        assert_equal(test_state.active_route_type, "Balanced")
        assert_equal(test_state.planned_speed, 14.0)
        assert_equal(len(test_state.route_summaries), 3)

        assert_equal(isinstance(handle_swap_endpoints(test_state), Page), True)
        assert_equal(test_state.dest_address, DEFAULT_START_LABEL)

        assert_equal(
            isinstance(handle_toggle_dark_mode(test_state), Page), True
        )
        assert_equal(test_state.dark_mode, True)
        assert_equal(
            isinstance(handle_toggle_dark_mode(test_state), Page), True
        )
        assert_equal(test_state.dark_mode, False)

        test_state.start_address = DEFAULT_START_LABEL
        test_state.dest_address = DEFAULT_DEST_LABEL
        assert_equal(
            isinstance(select_route_mode(test_state, "Direct"), Page), True
        )
        assert_equal(test_state.active_route_type, "Direct")

        assert_equal(
            isinstance(handle_toggle_advanced(test_state), Page), True
        )
        assert_equal(test_state.show_advanced, True)
        assert_equal(
            isinstance(handle_toggle_advanced(test_state), Page), True
        )
        assert_equal(test_state.show_advanced, False)

        assert_equal(
            isinstance(inspect_segment(test_state, "de_dir_1"), Page), True
        )
        assert_equal(test_state.selected_segment_id, "de_dir_1")

        assert_equal(
            isinstance(
                handle_save_settings(
                    test_state,
                    planned_speed="15.5",
                    start_time="17:15",
                    preferred_mode="Balanced",
                    units="km",
                    show_advanced=True,
                    dark_mode=True,
                ),
                Page,
            ),
            True,
        )
        assert_equal(test_state.current_page, "planner")
        assert_equal(test_state.units, "km")
        assert_equal(test_state.dark_mode, True)
    finally:
        if prev_offline is None:
            os.environ.pop("DRAFTER_OFFLINE_TESTS", None)
        else:
            os.environ["DRAFTER_OFFLINE_TESTS"] = prev_offline


if __name__ == "__main__":
    if os.environ.get("DRAFTER_RUN_TESTS", "").lower() in ("true", "1", "yes"):
        run_bakery_unit_tests()
    elif os.environ.get("DRAFTER_SKIP", "").lower() in ("true", "1", "yes"):
        run_bakery_unit_tests()
    elif "--compile" in sys.argv:
        run_bakery_unit_tests()
        start_server(State())
    else:
        start_server(
            State(),
            port=3000,
            host="0.0.0.0",
            open_browser=False,
            in_debug_mode=False,
            framed=False,
            use_reloader=False,
        )
