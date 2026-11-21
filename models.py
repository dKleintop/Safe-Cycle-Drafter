"""models.py - Core Python dataclasses for SafeCycle (Python + Drafter).

Advanced technique note:
- Uses `dataclasses.field(default_factory=list)` (beyond introductory CS1) so
  each dataclass instance receives its own independent list instead of sharing
  a single mutable default list across instances.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Coordinate:
    """Geographic latitude and longitude pair in decimal degrees."""

    latitude: float
    longitude: float

    def to_tuple(self) -> tuple[float, float]:
        """Return this coordinate as a (latitude, longitude) tuple."""
        return (self.latitude, self.longitude)


@dataclass
class RouteSummary:
    """Compact summary of a generated route option stored in Drafter State."""

    route_type: str
    safety_score: float
    distance_km: float
    duration_mins: float
    bike_infra_pct: float
    high_risk_count: int


@dataclass
class CrashRecord:
    """Historical bicycle collision record for a road segment."""

    total_crashes: int = 0
    severe_injuries: int = 0
    fatalities: int = 0
    date_range: str = "2022-2025"
    data_source: str = "Municipal Vision Zero & State DOT Crash Ledger"
    limitations: str = (
        "Only police-reported bicycle collisions are recorded; near-misses and "
        "unreported minor falls are excluded."
    )


@dataclass
class RoadSegment:
    """Evaluated road or trail segment with safety attributes and score."""

    segment_id: str
    name: str
    coordinates: List[Coordinate]
    length_km: float
    infrastructure: str
    speed_limit_mph: Optional[int]
    traffic_exposure: str
    crash_record: Optional[CrashRecord]
    intersection_risk: str
    safety_score: float = 0.0
    confidence: str = "MEDIUM"
    risk_category: str = "MODERATE"
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    evidence_notes: str = ""
    safer_alternative: str = ""


@dataclass
class RouteOption:
    """Candidate bicycle route option with safety metrics and segments."""

    route_type: str
    total_distance_km: float
    estimated_duration_mins: float
    overall_safety_score: float
    high_risk_segments_count: int
    bike_infrastructure_percentage: float
    major_intersections_count: int
    warnings: List[str]
    segments: List[RoadSegment]
    selection_rationale: str
    confidence_level: str = "MEDIUM"
    elevation_gain_m: float = 24.0
    corridor_summary: str = ""
    routing_source: str = "Local Safety Graph"
