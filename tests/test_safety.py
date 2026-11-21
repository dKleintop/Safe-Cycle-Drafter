"""tests/test_safety.py - Unit tests for road safety scoring with bakery."""

import os
import sys
import unittest

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR: str = os.path.join(BASE_DIR, ".py311_packages")
if os.path.exists(PKG_DIR) and PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bakery import assert_equal  # noqa: E402
import bakery.assertions as bakery_assertions  # noqa: E402
from models import CrashRecord  # noqa: E402
from safety import (  # noqa: E402
    determine_risk_category,
    evaluate_road_safety,
    get_risk_color_hex,
)


class TestSafetyScoring(unittest.TestCase):
    """Unit tests verifying transparent cycling risk scoring behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Silence verbose pass output while keeping bakery failure reports."""
        bakery_assertions.QUIET = True

    def test_protected_path_scores_higher_than_high_speed_arterial(
        self,
    ) -> None:
        """Protected off-street paths must vastly outscore 40 mph arterials."""
        safe_score, safe_cat, safe_conf, _, _, _ = evaluate_road_safety(
            infrastructure="protected_bike_path",
            speed_limit_mph=15,
            traffic_exposure="very_low",
            crash_record=CrashRecord(0, 0, 0),
            intersection_risk="low",
        )
        risky_score, risky_cat, risky_conf, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=40,
            traffic_exposure="heavy",
            crash_record=CrashRecord(6, 2, 1),
            intersection_risk="high_conflict",
        )
        self.assertTrue(assert_equal(safe_score > risky_score, True))
        self.assertTrue(assert_equal(safe_score > 85.0, True))
        self.assertTrue(assert_equal(safe_cat, "LOWER_RISK"))
        self.assertTrue(assert_equal(safe_conf, "HIGH"))
        self.assertTrue(assert_equal(risky_score < 35.0, True))
        self.assertTrue(assert_equal(risky_cat, "HIGH_RISK"))
        self.assertTrue(assert_equal(risky_conf, "HIGH"))

    def test_missing_data_reduces_confidence_and_avoids_high_score(
        self,
    ) -> None:
        """Missing roadway evidence must yield INSUFFICIENT/UNKNOWN status."""
        score, category, confidence, _, negatives, _ = evaluate_road_safety(
            infrastructure="unknown",
            speed_limit_mph=None,
            traffic_exposure="unknown",
            crash_record=None,
            intersection_risk="unknown",
        )
        self.assertTrue(assert_equal(score < 60.0, True))
        self.assertTrue(assert_equal(confidence, "INSUFFICIENT"))
        self.assertTrue(assert_equal(category, "UNKNOWN"))
        self.assertTrue(assert_equal(len(negatives) >= 4, True))

    def test_zero_crashes_alone_never_masks_dangerous_arterial(self) -> None:
        """Zero crashes must not make an unprotected 40 mph road look safe."""
        score, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=40,
            traffic_exposure="heavy",
            crash_record=CrashRecord(0, 0, 0),
            intersection_risk="high_conflict",
        )
        self.assertTrue(assert_equal(score < 50.0, True))

    def test_paved_shoulder_outperforms_no_infrastructure(self) -> None:
        """Dedicated paved bike shoulders must outscore unprotected roads."""
        shoulder_score, _, _, shoulder_pos, _, _ = evaluate_road_safety(
            infrastructure="paved_shoulder",
            speed_limit_mph=30,
            traffic_exposure="moderate",
            crash_record=CrashRecord(0, 0, 0),
            intersection_risk="low",
        )
        none_score, _, _, _, _, _ = evaluate_road_safety(
            infrastructure="none",
            speed_limit_mph=30,
            traffic_exposure="moderate",
            crash_record=CrashRecord(0, 0, 0),
            intersection_risk="low",
        )
        self.assertTrue(assert_equal(shoulder_score > none_score, True))
        has_shoulder_text = any("shoulder" in note.lower() for note in shoulder_pos)
        self.assertTrue(assert_equal(has_shoulder_text, True))

    def test_risk_band_thresholds_and_colors(self) -> None:
        """Verify risk category boundaries and semantic hex colors."""
        self.assertTrue(
            assert_equal(determine_risk_category(88.0, "HIGH"), "LOWER_RISK")
        )
        self.assertTrue(
            assert_equal(determine_risk_category(65.0, "MEDIUM"), "MODERATE")
        )
        self.assertTrue(
            assert_equal(determine_risk_category(45.0, "HIGH"), "ELEVATED")
        )
        self.assertTrue(
            assert_equal(determine_risk_category(22.0, "HIGH"), "HIGH_RISK")
        )
        self.assertTrue(
            assert_equal(
                determine_risk_category(95.0, "INSUFFICIENT"), "UNKNOWN"
            )
        )
        self.assertTrue(
            assert_equal(get_risk_color_hex("LOWER_RISK"), "#15803d")
        )
        self.assertTrue(
            assert_equal(get_risk_color_hex("HIGH_RISK"), "#b91c1c")
        )


if __name__ == "__main__":
    unittest.main()
