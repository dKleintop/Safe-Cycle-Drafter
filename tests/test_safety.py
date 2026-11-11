"""
tests/test_safety.py - Automated tests for road safety scoring logic
"""
import unittest
from models import CrashRecord
from safety import evaluate_road_safety, determine_risk_category

class TestSafetyScoring(unittest.TestCase):

    def test_protected_bike_lane_vs_unprotected_high_speed(self):
        """A protected bike lane should score significantly higher than an unprotected high-speed road."""
        score_protected, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="protected_bike_path",
            speed_limit_mph=15,
            traffic_exposure="very_low",
            crash_record=CrashRecord(total_crashes=0, severe_injuries=0, fatalities=0),
            intersection_risk="low"
        )

        score_unprotected, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=40,
            traffic_exposure="heavy",
            crash_record=CrashRecord(total_crashes=6, severe_injuries=2, fatalities=1),
            intersection_risk="high_conflict"
        )

        self.assertGreater(score_protected, score_unprotected)
        self.assertGreater(score_protected, 80.0)
        self.assertLess(score_unprotected, 40.0)

    def test_high_speed_heavy_traffic_vs_low_speed_with_infrastructure(self):
        """High-speed road with heavy traffic receives worse score than low-speed road with bike infra."""
        score_arterial, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=35,
            traffic_exposure="heavy",
            crash_record=None,
            intersection_risk="high_conflict"
        )

        score_greenway, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="separated_lane",
            speed_limit_mph=20,
            traffic_exposure="low",
            crash_record=None,
            intersection_risk="low"
        )

        self.assertLess(score_arterial, score_greenway)

    def test_missing_data_does_not_award_high_score(self):
        """A road with missing safety data must not automatically receive a high safety score."""
        score_missing, cat, conf, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=None,
            traffic_exposure="unknown",
            crash_record=None,
            intersection_risk="moderate"
        )

        # Missing attributes should not yield > 70
        self.assertLess(score_missing, 70.0)
        self.assertIn(conf, ["LOW", "INSUFFICIENT"])

    def test_zero_crashes_alone_does_not_grant_100_on_dangerous_road(self):
        """A road with 0 reported crashes but 40 mph and no bike lane must not score 100."""
        score, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=40,
            traffic_exposure="heavy",
            crash_record=CrashRecord(total_crashes=0),
            intersection_risk="high_conflict"
        )
        self.assertLess(score, 50.0)

    def test_paved_shoulder_vs_shared_lane_and_none(self):
        """Paved bicycle shoulders should provide measurable protection over shared lanes and no infrastructure."""
        score_shoulder, _, _, pos_shoulder, _, _ = evaluate_road_safety(
            infrastructure="paved_shoulder",
            speed_limit_mph=35,
            traffic_exposure="moderate",
            crash_record=CrashRecord(total_crashes=0),
            intersection_risk="low"
        )
        score_none, _, _, _, neg_none, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=35,
            traffic_exposure="moderate",
            crash_record=CrashRecord(total_crashes=0),
            intersection_risk="low"
        )
        self.assertGreater(score_shoulder, score_none)
        self.assertTrue(any("shoulder" in p.lower() for p in pos_shoulder))

    def test_risk_categories_and_colors(self):
        """Test proper thresholding for risk categories."""
        self.assertEqual(determine_risk_category(85.0, "HIGH"), "LOWER_RISK")
        self.assertEqual(determine_risk_category(68.0, "MEDIUM"), "MODERATE")
        self.assertEqual(determine_risk_category(48.0, "HIGH"), "ELEVATED")
        self.assertEqual(determine_risk_category(25.0, "HIGH"), "HIGH_RISK")
        self.assertEqual(determine_risk_category(90.0, "INSUFFICIENT"), "UNKNOWN")

if __name__ == '__main__':
    unittest.main()
