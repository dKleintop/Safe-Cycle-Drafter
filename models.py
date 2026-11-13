"""
models.py - Core Python data structures for SafeCycle Drafter
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Coordinate:
    """Geographic latitude and longitude pair in decimal degrees."""

    latitude: float
    longitude: float

    def to_tuple(self) -> tuple[float, float]:
        """Return coordinate as a (latitude, longitude) tuple."""
        return (self.latitude, self.longitude)


@dataclass
class HazardReport:
    """Community-submitted road safety hazard report stored in application state."""

    road: str
    issue: str
    reported_at: str


@dataclass
class CrashRecord:
    """Historical bicycle collision record for a road segment."""

    total_crashes: int = 0
    severe_injuries: int = 0
    fatalities: int = 0
    date_range: str = "2022-2025"
    data_source: str = "Official Municipal Vision Zero Database"
    limitations: str = "Only police-reported bicycle incidents are recorded."


@dataclass
class RoadSegment:
    """Evaluated road or trail segment with safety attributes and score."""

    segment_id: str
    name: str
    coordinates: List[Coordinate]
    length_km: float
    # Supported infrastructure: 'protected_bike_path', 'separated_lane',
    # 'painted_lane', 'paved_shoulder', 'traffic_calmed_street', 'shared_lane', 'none'
    infrastructure: str
    speed_limit_mph: Optional[int]
    traffic_exposure: str  # 'very_low', 'low', 'moderate', 'high', 'heavy'
    crash_record: Optional[CrashRecord]
    intersection_risk: str  # 'low', 'moderate', 'high_conflict'
    safety_score: float = 0.0  # 0 to 100
    confidence: str = "MEDIUM"  # 'HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT'
    risk_category: str = "MODERATE"  # 'LOWER_RISK', 'MODERATE', 'ELEVATED', 'HIGH_RISK', 'UNKNOWN'
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    evidence_notes: str = ""
    safer_alternative: str = ""


@dataclass
class TurnInstruction:
    """Turn-by-turn cycling navigation step along a route."""

    step_number: int
    instruction: str
    distance_m: float
    street_name: str
    safety_warning: Optional[str] = None
    icon: str = "straight"  # 'turn_left', 'turn_right', 'straight', 'start', 'end'


@dataclass
class RouteOption:
    """Candidate bicycle route option with safety metrics and segments."""

    route_type: str  # 'Safest', 'Balanced', 'Direct'
    total_distance_km: float
    estimated_duration_mins: float
    overall_safety_score: float
    high_risk_segments_count: int
    bike_infrastructure_percentage: float
    major_intersections_count: int
    warnings: List[str]
    segments: List[RoadSegment]
    turn_instructions: List[TurnInstruction]
    selection_rationale: str
    confidence_level: str = "MEDIUM"
    elevation_gain_m: float = 24.0


@dataclass
class SavedRouteItem:
    """Bookmarked cycling route entry persisted to browser or JSON storage."""

    route_id: str
    name: str
    start_label: str
    dest_label: str
    route_type: str
    distance_km: float
    duration_mins: float
    safety_score: float
    created_at: str
    gpx_content: str

