"""
safety.py - Road safety scoring engine and risk explanations for SafeCycle
"""
from typing import Tuple, List, Optional
from models import RoadSegment, CrashRecord

# Base design weights (must sum to 1.0)
WEIGHT_INFRASTRUCTURE = 0.30
WEIGHT_SPEED = 0.20
WEIGHT_TRAFFIC = 0.15
WEIGHT_CRASH_HISTORY = 0.20
WEIGHT_INTERSECTION = 0.15

INFRASTRUCTURE_SCORES = {
    "protected_bike_path": 100.0,    # Physically separated off-road trail or barrier-separated cycle track
    "separated_lane": 85.0,          # Bollards, planter boxes, or parking-protected bike lane
    "painted_lane": 60.0,            # Standard painted bicycle lane on road shoulder
    "paved_shoulder": 55.0,          # Wide paved bicycle shoulder (DelDOT / State DOT designated bike shoulder)
    "shoulder": 55.0,                # Paved road shoulder suitable for cycling
    "bike_shoulder": 55.0,           # Dedicated bicycle shoulder
    "shared_lane": 35.0,             # Sharrows on shared motor vehicle roadway
    "traffic_calmed_street": 65.0,   # Neighborhood greenway, speed bumps, 15mph limit
    "unknown": 45.0,                 # Unconfirmed or unmapped infrastructure (neutral baseline)
    "none": 15.0                     # No dedicated bike infrastructure
}

SPEED_SCORES = {
    15: 100.0,
    20: 85.0,
    25: 70.0,
    30: 45.0,
    35: 25.0,
    40: 10.0,
    45: 5.0,
    50: 0.0
}

TRAFFIC_SCORES = {
    "very_low": 95.0,    # Cul-de-sac, quiet residential lane (<500 vehicles/day)
    "low": 80.0,         # Local residential street (~1,000-2,000 vehicles/day)
    "moderate": 50.0,    # Collector street (~5,000-10,000 vehicles/day)
    "high": 25.0,        # Minor arterial (~15,000 vehicles/day)
    "heavy": 5.0         # Major multi-lane arterial / freight corridor (>25,000 vehicles/day)
}

INTERSECTION_SCORES = {
    "low": 90.0,            # Protected bike signal, mini-roundabout, or stop sign on quiet street
    "moderate": 60.0,       # Standard signalized intersection with bicycle crosswalk
    "high_conflict": 20.0   # Multi-lane arterial crossing, highway off-ramp merge, high turn conflicts
}

def determine_risk_category(score: float, confidence: str) -> str:
    """Categorize score into standard color-coded risk bands."""
    if confidence == "INSUFFICIENT":
        return "UNKNOWN"
    if score >= 80.0:
        return "LOWER_RISK"   # Green
    elif score >= 60.0:
        return "MODERATE"     # Yellow
    elif score >= 40.0:
        return "ELEVATED"     # Orange
    else:
        return "HIGH_RISK"    # Red

def get_risk_color_hex(category: str) -> str:
    """Return map and badge hex color for each risk category."""
    mapping = {
        "LOWER_RISK": "#16a34a",   # Green (Tailwind green-600)
        "MODERATE": "#ca8a04",     # Yellow (Tailwind yellow-600)
        "ELEVATED": "#ea580c",     # Orange (Tailwind orange-600)
        "HIGH_RISK": "#dc2626",    # Red (Tailwind red-600)
        "UNKNOWN": "#6b7280"       # Gray (Tailwind gray-500)
    }
    return mapping.get(category, "#6b7280")

def compute_speed_score(speed_mph: Optional[int]) -> Tuple[float, bool]:
    """Score vehicle speed. Returns (subscore, is_known)."""
    if speed_mph is None:
        return (40.0, False)  # Unknown default: assume average urban collector, low confidence
    if speed_mph <= 15:
        return (SPEED_SCORES[15], True)
    elif speed_mph <= 20:
        return (SPEED_SCORES[20], True)
    elif speed_mph <= 25:
        return (SPEED_SCORES[25], True)
    elif speed_mph <= 30:
        return (SPEED_SCORES[30], True)
    elif speed_mph <= 35:
        return (SPEED_SCORES[35], True)
    elif speed_mph <= 40:
        return (SPEED_SCORES[40], True)
    else:
        return (0.0, True)

def compute_crash_score(crash_record: Optional[CrashRecord]) -> Tuple[float, bool]:
    """
    Score crash history.
    Never award a perfect score simply because no crash was recorded.
    A baseline score of 80 is given for 0 reported crashes, subject to exposure.
    Each crash deducts points, with heavy penalties for severe injuries and fatalities.
    """
    if crash_record is None:
        return (50.0, False)  # Missing crash dataset: neutral midpoint with reduced confidence
    
    total = crash_record.total_crashes
    severe = crash_record.severe_injuries
    fatal = crash_record.fatalities

    if total == 0:
        return (82.0, True)
    
    # Penalty calculation:
    # Baseline 75 minus minor crashes, severe injuries (-25 each), fatalities (-50)
    penalty = (total * 8.0) + (severe * 22.0) + (fatal * 45.0)
    score = max(0.0, 75.0 - penalty)
    return (score, True)

def evaluate_road_safety(
    infrastructure: str,
    speed_limit_mph: Optional[int],
    traffic_exposure: str,
    crash_record: Optional[CrashRecord],
    intersection_risk: str = "moderate"
) -> Tuple[float, str, str, List[str], List[str], str]:
    """
    Compute comprehensive safety score and evidence factor breakdown.
    Returns:
        (safety_score, risk_category, confidence_level, positive_factors, negative_factors, notes)
    """
    positives = []
    negatives = []
    known_data_points = 0
    total_data_points = 5

    # 1. Infrastructure (30%)
    infra_key = infrastructure.lower().strip()
    infra_score = INFRASTRUCTURE_SCORES.get(infra_key, 25.0)
    if infra_key in ["protected_bike_path", "separated_lane"]:
        positives.append(f"Dedicated physical separation from motor vehicle traffic (+{int(infra_score * WEIGHT_INFRASTRUCTURE)} pts)")
        known_data_points += 1
    elif infra_key == "traffic_calmed_street":
        positives.append(f"Traffic-calmed neighborhood greenway (+{int(infra_score * WEIGHT_INFRASTRUCTURE)} pts)")
        known_data_points += 1
    elif infra_key == "painted_lane":
        positives.append(f"Designated painted bicycle lane (+{int(infra_score * WEIGHT_INFRASTRUCTURE)} pts)")
        known_data_points += 1
    elif infra_key in ["paved_shoulder", "shoulder", "bike_shoulder"]:
        positives.append(f"Dedicated paved bicycle shoulder provides physical separation from motor traffic lanes (+{int(infra_score * WEIGHT_INFRASTRUCTURE)} pts)")
        known_data_points += 1
    elif infra_key == "shared_lane":
        negatives.append("Shared lane (sharrow): no physical or painted separation from traffic")
        known_data_points += 1
    else:
        negatives.append("No bicycle infrastructure: cyclists must mix directly with motor traffic")
        known_data_points += 1

    # 2. Vehicle Speed (20%)
    speed_subscore, speed_known = compute_speed_score(speed_limit_mph)
    if speed_known:
        known_data_points += 1
        if speed_limit_mph and speed_limit_mph <= 20:
            positives.append(f"Low motor vehicle speed limit ({speed_limit_mph} mph) reduces impact severity")
        elif speed_limit_mph and speed_limit_mph >= 35:
            negatives.append(f"High vehicle speed limit ({speed_limit_mph} mph): severe cyclist injury risk")
        elif speed_limit_mph and speed_limit_mph >= 25:
            negatives.append(f"Moderate vehicle speed limit ({speed_limit_mph} mph)")
    else:
        negatives.append("Speed limit not mapped in database (estimated based on road class)")

    # 3. Traffic Exposure (15%)
    traffic_key = traffic_exposure.lower().strip()
    if traffic_key in TRAFFIC_SCORES:
        traffic_subscore = TRAFFIC_SCORES[traffic_key]
        known_data_points += 1
        if traffic_key in ["very_low", "low"]:
            positives.append(f"Low vehicular traffic volume ({traffic_key.replace('_', ' ')})")
        elif traffic_key in ["high", "heavy"]:
            negatives.append(f"Heavy motor vehicle traffic and truck exposure ({traffic_key})")
    else:
        traffic_subscore = 40.0
        negatives.append("Traffic volume counts unverified")

    # 4. Crash History (20%)
    crash_subscore, crash_known = compute_crash_score(crash_record)
    if crash_known and crash_record:
        known_data_points += 1
        if crash_record.total_crashes == 0:
            positives.append(f"Zero reported bicycle collisions in official database ({crash_record.date_range})")
        else:
            negatives.append(
                f"{crash_record.total_crashes} reported bicycle crash(es) ({crash_record.severe_injuries} severe, {crash_record.fatalities} fatal) ({crash_record.date_range})"
            )
    else:
        negatives.append("Official municipal crash history data missing for this segment")

    # 5. Intersection & Roadway (15%)
    inter_key = intersection_risk.lower().strip()
    inter_subscore = INTERSECTION_SCORES.get(inter_key, 50.0)
    known_data_points += 1
    if inter_key == "low":
        positives.append("Protected bicycle crossing signal or low-conflict junction")
    elif inter_key == "high_conflict":
        negatives.append("Documented intersection conflict hotspot / multi-lane turning hazard")

    # Final weighted score
    overall_score = (
        infra_score * WEIGHT_INFRASTRUCTURE +
        speed_subscore * WEIGHT_SPEED +
        traffic_subscore * WEIGHT_TRAFFIC +
        crash_subscore * WEIGHT_CRASH_HISTORY +
        inter_subscore * WEIGHT_INTERSECTION
    )
    overall_score = round(max(0.0, min(100.0, overall_score)), 1)

    # Confidence calculation
    if known_data_points >= 4 and crash_known and speed_known:
        confidence = "HIGH"
    elif known_data_points >= 3:
        confidence = "MEDIUM"
    elif known_data_points >= 2:
        confidence = "LOW"
    else:
        confidence = "INSUFFICIENT"

    category = determine_risk_category(overall_score, confidence)
    notes = f"Evidence based on {known_data_points}/{total_data_points} confirmed attributes. Calibrated model v2.1."

    return (overall_score, category, confidence, positives, negatives, notes)
