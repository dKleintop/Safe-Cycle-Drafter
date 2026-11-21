"""safety.py - Transparent, evidence-based road safety scoring engine."""

from typing import Dict, List, Optional, Tuple
from models import CrashRecord

# Configurable preliminary model weights (sum = 1.00)
WEIGHT_INFRASTRUCTURE: float = 0.30
WEIGHT_SPEED: float = 0.20
WEIGHT_TRAFFIC: float = 0.15
WEIGHT_CRASH_HISTORY: float = 0.20
WEIGHT_INTERSECTION: float = 0.15

INFRASTRUCTURE_SCORES: Dict[str, float] = {
    "protected_bike_path": 100.0,
    "separated_lane": 92.0,
    "traffic_calmed_street": 78.0,
    "painted_lane": 68.0,
    "paved_shoulder": 62.0,
    "shoulder": 62.0,
    "bike_shoulder": 62.0,
    "shared_lane": 38.0,
    "none": 15.0,
}

INFRASTRUCTURE_LABELS: Dict[str, str] = {
    "protected_bike_path": "Protected Off-Street Bike Path",
    "separated_lane": "Physically Separated Cycle Track",
    "traffic_calmed_street": "Traffic-Calmed Neighborhood Greenway",
    "painted_lane": "Painted Bicycle Lane",
    "paved_shoulder": "Dedicated Paved Bike Shoulder",
    "shoulder": "Dedicated Paved Bike Shoulder",
    "bike_shoulder": "Dedicated Paved Bike Shoulder",
    "shared_lane": "Shared Traffic Lane (Sharrow)",
    "none": "No Dedicated Bike Infrastructure",
}

SPEED_SCORES: Dict[int, float] = {
    15: 100.0,
    20: 90.0,
    25: 72.0,
    30: 48.0,
    35: 25.0,
    40: 10.0,
}

TRAFFIC_SCORES: Dict[str, float] = {
    "very_low": 98.0,
    "low": 82.0,
    "moderate": 55.0,
    "high": 25.0,
    "heavy": 5.0,
}

INTERSECTION_SCORES: Dict[str, float] = {
    "low": 90.0,
    "moderate": 60.0,
    "high_conflict": 20.0,
}

RISK_LABELS: Dict[str, str] = {
    "LOWER_RISK": "Lower Risk (80-100)",
    "MODERATE": "Moderate Risk (60-79)",
    "ELEVATED": "Elevated Risk (40-59)",
    "HIGH_RISK": "High Risk (<40)",
    "UNKNOWN": "Insufficient Data",
}

RISK_COLOR_HEX: Dict[str, str] = {
    "LOWER_RISK": "#15803d",
    "MODERATE": "#b45309",
    "ELEVATED": "#c2410c",
    "HIGH_RISK": "#b91c1c",
    "UNKNOWN": "#64748b",
}

DATA_SOURCES_METADATA: Dict[str, Dict[str, str]] = {
    "osm": {
        "name": "OpenStreetMap Road & Cycleway Tagging",
        "coverage": (
            "Cycle paths, painted lanes, paved shoulders, speed limits, "
            "and road classifications."
        ),
        "limitations": (
            "Community-maintained tags may lag behind recent repaving, "
            "construction detours, or temporary bike lane obstructions."
        ),
    },
    "vision_zero": {
        "name": "Municipal Vision Zero & State DOT Crash Records (2022-2025)",
        "coverage": (
            "Police-reported bicycle collisions, severe injuries, and "
            "fatalities by corridor."
        ),
        "limitations": (
            "Near-misses, unreported dooring incidents, and minor solo falls "
            "are excluded. Zero reported crashes never guarantees safety."
        ),
    },
    "traffic_counts": {
        "name": "Annual Average Daily Traffic (AADT) & Road Class Estimates",
        "coverage": (
            "Estimated motor vehicle volume, arterial classification, and "
            "freight exposure."
        ),
        "limitations": (
            "Peak rush-hour surges, school zones, and weather changes can "
            "temporarily raise exposure beyond daily averages."
        ),
    },
}


def determine_risk_category(score: float, confidence: str) -> str:
    """Categorize a 0-100 safety score into standard risk bands."""
    if confidence == "INSUFFICIENT":
        return "UNKNOWN"
    if score >= 80.0:
        return "LOWER_RISK"
    if score >= 60.0:
        return "MODERATE"
    if score >= 40.0:
        return "ELEVATED"
    return "HIGH_RISK"


def get_risk_color_hex(category: str) -> str:
    """Return the hex color string corresponding to a risk category."""
    return RISK_COLOR_HEX.get(category, "#64748b")


def get_risk_label(category: str) -> str:
    """Return a plain-English risk band label for a risk category."""
    return RISK_LABELS.get(category, "Unknown Risk")


def format_infrastructure_label(infrastructure_key: str) -> str:
    """Convert an internal infrastructure key into human-readable text."""
    normalized_key = infrastructure_key.lower().strip()
    return INFRASTRUCTURE_LABELS.get(normalized_key, "Unclassified Roadway")


def compute_speed_score(speed_mph: Optional[int]) -> Tuple[float, bool]:
    """Score posted vehicle speed limit and return (subscore, is_known)."""
    if speed_mph is None:
        return (40.0, False)
    if speed_mph <= 15:
        return (SPEED_SCORES[15], True)
    if speed_mph <= 20:
        return (SPEED_SCORES[20], True)
    if speed_mph <= 25:
        return (SPEED_SCORES[25], True)
    if speed_mph <= 30:
        return (SPEED_SCORES[30], True)
    if speed_mph <= 35:
        return (SPEED_SCORES[35], True)
    if speed_mph <= 40:
        return (SPEED_SCORES[40], True)
    return (0.0, True)


def compute_crash_score(
    crash_record: Optional[CrashRecord],
) -> Tuple[float, bool]:
    """Score reported bicycle crash history without awarding a blind 100."""
    if crash_record is None:
        return (50.0, False)
    if crash_record.total_crashes == 0:
        return (82.0, True)
    penalty = (
        (crash_record.total_crashes * 8.0)
        + (crash_record.severe_injuries * 22.0)
        + (crash_record.fatalities * 45.0)
    )
    return (max(0.0, 75.0 - penalty), True)


def score_infrastructure_factor(
    infrastructure: str,
) -> Tuple[float, bool, List[str], List[str]]:
    """Evaluate bicycle infrastructure and return (score, known, pos, neg)."""
    positives: List[str] = []
    negatives: List[str] = []
    infra_key = infrastructure.lower().strip()
    infra_score = INFRASTRUCTURE_SCORES.get(infra_key, 25.0)
    weighted_pts = int(infra_score * WEIGHT_INFRASTRUCTURE)

    if infra_key in ("protected_bike_path", "separated_lane"):
        positives.append(
            f"Physical separation from motor vehicles (+{weighted_pts} pts)"
        )
        return (infra_score, True, positives, negatives)
    if infra_key == "traffic_calmed_street":
        positives.append(
            f"Traffic-calmed neighborhood greenway (+{weighted_pts} pts)"
        )
        return (infra_score, True, positives, negatives)
    if infra_key == "painted_lane":
        positives.append(
            f"Designated painted bicycle lane (+{weighted_pts} pts)"
        )
        return (infra_score, True, positives, negatives)
    if infra_key in ("paved_shoulder", "shoulder", "bike_shoulder"):
        positives.append(
            f"Dedicated paved bicycle shoulder (+{weighted_pts} pts)"
        )
        return (infra_score, True, positives, negatives)
    if infra_key == "shared_lane":
        negatives.append(
            "Shared lane markings only: no physical separation from traffic"
        )
        return (infra_score, True, positives, negatives)
    if infra_key == "none":
        negatives.append(
            "No dedicated bicycle infrastructure: cyclists ride in traffic"
        )
        return (infra_score, True, positives, negatives)

    negatives.append("Bicycle facility classification missing in database")
    return (infra_score, False, positives, negatives)


def score_traffic_factor(
    traffic_exposure: str,
) -> Tuple[float, bool, List[str], List[str]]:
    """Evaluate motor vehicle traffic exposure and return factor breakdown."""
    positives: List[str] = []
    negatives: List[str] = []
    traffic_key = traffic_exposure.lower().strip()
    if traffic_key in TRAFFIC_SCORES:
        subscore = TRAFFIC_SCORES[traffic_key]
        if traffic_key in ("very_low", "low"):
            readable = traffic_key.replace("_", " ")
            positives.append(f"Low motor vehicle volume ({readable})")
        elif traffic_key in ("high", "heavy"):
            negatives.append(
                f"High motor vehicle and freight exposure ({traffic_key})"
            )
        return (subscore, True, positives, negatives)
    negatives.append("Traffic volume counts unknown for this segment")
    return (40.0, False, positives, negatives)


def score_intersection_factor(
    intersection_risk: str,
) -> Tuple[float, bool, List[str], List[str]]:
    """Evaluate intersection conflict risk and return factor breakdown."""
    positives: List[str] = []
    negatives: List[str] = []
    intersection_key = intersection_risk.lower().strip()
    if intersection_key in INTERSECTION_SCORES:
        subscore = INTERSECTION_SCORES[intersection_key]
        if intersection_key == "low":
            positives.append("Low-conflict junctions or protected crossings")
        elif intersection_key == "high_conflict":
            negatives.append(
                "Documented high-conflict multi-lane intersections or ramps"
            )
        return (subscore, True, positives, negatives)
    negatives.append("Intersection conflict profile unverified")
    return (50.0, False, positives, negatives)


def compute_confidence_level(
    known_points: int, crash_known: bool, speed_known: bool
) -> str:
    """Compute evidence confidence band from verified roadway attributes."""
    if known_points >= 4 and crash_known and speed_known:
        return "HIGH"
    if known_points >= 3:
        return "MEDIUM"
    if known_points >= 2:
        return "LOW"
    return "INSUFFICIENT"


def evaluate_road_safety(
    infrastructure: str,
    speed_limit_mph: Optional[int],
    traffic_exposure: str,
    crash_record: Optional[CrashRecord],
    intersection_risk: str = "moderate",
) -> Tuple[float, str, str, List[str], List[str], str]:
    """Compute 0-100 safety score, risk band, confidence, and evidence."""
    positives: List[str] = []
    negatives: List[str] = []
    known_data_points = 0
    total_data_points = 5

    infra_score, infra_known, infra_pos, infra_neg = (
        score_infrastructure_factor(infrastructure)
    )
    positives.extend(infra_pos)
    negatives.extend(infra_neg)
    if infra_known:
        known_data_points += 1

    speed_subscore, speed_known = compute_speed_score(speed_limit_mph)
    if speed_known and speed_limit_mph is not None:
        known_data_points += 1
        if speed_limit_mph <= 20:
            positives.append(
                f"Low speed limit ({speed_limit_mph} mph) reduces severity"
            )
        elif speed_limit_mph >= 35:
            negatives.append(
                f"High speed limit ({speed_limit_mph} mph) elevates risk"
            )
        elif speed_limit_mph >= 25:
            negatives.append(
                f"Moderate speed limit ({speed_limit_mph} mph)"
            )
    else:
        negatives.append("Speed limit unverified (conservative penalty)")

    traffic_score, traffic_known, traffic_pos, traffic_neg = (
        score_traffic_factor(traffic_exposure)
    )
    positives.extend(traffic_pos)
    negatives.extend(traffic_neg)
    if traffic_known:
        known_data_points += 1

    crash_subscore, crash_known = compute_crash_score(crash_record)
    if crash_known and crash_record is not None:
        known_data_points += 1
        if crash_record.total_crashes == 0:
            positives.append(
                f"Zero reported bike crashes ({crash_record.date_range})"
            )
        else:
            negatives.append(
                f"{crash_record.total_crashes} bike crash(es) "
                f"({crash_record.severe_injuries} severe, "
                f"{crash_record.fatalities} fatal) in {crash_record.date_range}"
            )
    else:
        negatives.append("Official crash history missing (lower confidence)")

    inter_score, inter_known, inter_pos, inter_neg = score_intersection_factor(
        intersection_risk
    )
    positives.extend(inter_pos)
    negatives.extend(inter_neg)
    if inter_known:
        known_data_points += 1

    raw_score = (
        infra_score * WEIGHT_INFRASTRUCTURE
        + speed_subscore * WEIGHT_SPEED
        + traffic_score * WEIGHT_TRAFFIC
        + crash_subscore * WEIGHT_CRASH_HISTORY
        + inter_score * WEIGHT_INTERSECTION
    )
    overall_score = round(max(0.0, min(100.0, raw_score)), 1)
    confidence = compute_confidence_level(
        known_data_points, crash_known, speed_known
    )
    category = determine_risk_category(overall_score, confidence)
    notes = (
        f"Evidence synthesized from {known_data_points}/{total_data_points} "
        f"verified roadway attributes (Confidence: {confidence})."
    )
    return (overall_score, category, confidence, positives, negatives, notes)
