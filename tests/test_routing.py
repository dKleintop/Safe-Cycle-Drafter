"""
tests/test_routing.py - Automated tests for routing engine, mode selection, and consistency
"""
import unittest
from unittest.mock import patch
from models import Coordinate
from routing import plan_bicycle_routes, SafetyRoutingGraph
from geocoding import geocode_address

class TestRoutingEngine(unittest.TestCase):

    def setUp(self) -> None:
        """Initialize shared start and destination coordinates for routing tests."""
        self.start = Coordinate(40.7661, -73.9772)  # Central Park South
        self.dest = Coordinate(40.7126, -74.0048)   # Brooklyn Bridge

    def test_safest_mode_prefers_lower_risk(self) -> None:
        """Safest mode should produce higher overall safety score than Direct mode."""
        with (
            patch("routing.fetch_osrm_bike_route", return_value=None),
            patch("routing.fetch_osrm_bike_routes", return_value=[], create=True),
        ):
            routes = plan_bicycle_routes(
                self.start, self.dest,
                "Central Park South", "Brooklyn Bridge",
                max_risk_tolerance="low", detour_tolerance="50%"
            )
        self.assertIn("Safest", routes)
        self.assertIn("Direct", routes)
        self.assertIn("Balanced", routes)

        safest = routes["Safest"]
        direct = routes["Direct"]

        # Safest route must have higher safety score
        self.assertGreater(safest.overall_safety_score, direct.overall_safety_score)
        # Safest route should have 0 or fewer high risk segments than direct
        self.assertLessEqual(safest.high_risk_segments_count, direct.high_risk_segments_count)
        # Direct route distance should be shorter or equal
        self.assertLessEqual(direct.total_distance_km, safest.total_distance_km)

    def test_balanced_mode_compromise(self) -> None:
        """Balanced mode should offer an intermediate distance and safety profile."""
        with (
            patch("routing.fetch_osrm_bike_route", return_value=None),
            patch("routing.fetch_osrm_bike_routes", return_value=[], create=True),
        ):
            routes = plan_bicycle_routes(
                self.start, self.dest,
                "Central Park South", "Brooklyn Bridge"
            )
        safest = routes["Safest"]
        balanced = routes["Balanced"]
        direct = routes["Direct"]

        # Balanced safety score should be between direct and safest (or close)
        self.assertGreaterEqual(balanced.overall_safety_score, direct.overall_safety_score)
        self.assertLessEqual(balanced.overall_safety_score, safest.overall_safety_score + 1.0)

    def test_units_consistency(self) -> None:
        """Distance and durations should use consistent units (km and minutes)."""
        with (
            patch("routing.fetch_osrm_bike_route", return_value=None),
            patch("routing.fetch_osrm_bike_routes", return_value=[], create=True),
        ):
            routes = plan_bicycle_routes(
                self.start, self.dest,
                "Central Park South", "Brooklyn Bridge"
            )
        for mode, route in routes.items():
            self.assertGreater(route.total_distance_km, 0.5)
            self.assertLess(route.total_distance_km, 30.0)
            self.assertGreater(route.estimated_duration_mins, 2.0)
            # Duration in minutes at ~16km/h should roughly match (distance / 16) * 60
            expected_approx_mins = (route.total_distance_km / 16.0) * 60
            self.assertAlmostEqual(route.estimated_duration_mins, expected_approx_mins, delta=5.0)

    def test_empty_or_invalid_coordinates_handled_gracefully(self) -> None:
        """Geocoding empty string gives user-facing error message without crashing."""
        coord, msg = geocode_address("")
        self.assertIsNone(coord)
        self.assertIn("valid", msg.lower())

    def test_danger_not_hidden_on_direct_route(self) -> None:
        """Direct route must not hide dangerous segments: warnings or high-risk flags must be present."""
        with (
            patch("routing.fetch_osrm_bike_route", return_value=None),
            patch("routing.fetch_osrm_bike_routes", return_value=[], create=True),
        ):
            routes = plan_bicycle_routes(
                self.start, self.dest,
                "Central Park South", "Brooklyn Bridge"
            )
        direct = routes["Direct"]
        self.assertTrue(
            direct.high_risk_segments_count > 0 or len(direct.warnings) > 0,
            "Direct route must identify dangerous segments or warnings."
        )

    def test_accurate_road_corridors_and_speed_limits(self) -> None:
        """Corridor extraction and DOT speed lookup must assign verified speed limits to actual highway corridors."""
        from data_sources import get_accurate_road_attributes
        attrs_de72 = get_accurate_road_attributes("Sunset Lake Road (DE 72)", "Balanced")
        self.assertEqual(attrs_de72["speed_limit_mph"], 45)
        self.assertIn("DelDOT", attrs_de72["data_source"])

        attrs_wrangle = get_accurate_road_attributes("Wrangle Hill Road (DE 72)", "Direct")
        self.assertEqual(attrs_wrangle["speed_limit_mph"], 45)

        attrs_us40 = get_accurate_road_attributes("Pulaski Highway (US 40)", "Direct")
        self.assertEqual(attrs_us40["speed_limit_mph"], 50)
        self.assertEqual(attrs_us40["infrastructure"], "paved_shoulder")

        # Delaware Newark to Lums Pond direct corridor shoulders
        attrs_896 = get_accurate_road_attributes("South College Avenue (DE 896 South)", "Direct")
        self.assertEqual(attrs_896["speed_limit_mph"], 45)
        self.assertEqual(attrs_896["infrastructure"], "paved_shoulder")

        attrs_summit = get_accurate_road_attributes("Summit Bridge Road (DE 896)", "Direct")
        self.assertEqual(attrs_summit["speed_limit_mph"], 45)
        self.assertEqual(attrs_summit["infrastructure"], "paved_shoulder")

        attrs_howell = get_accurate_road_attributes("Howell School Road", "Direct")
        self.assertEqual(attrs_howell["speed_limit_mph"], 35)
        self.assertEqual(attrs_howell["infrastructure"], "paved_shoulder")

        attrs_buck = get_accurate_road_attributes("Buck Jersey Road", "Direct")
        self.assertEqual(attrs_buck["speed_limit_mph"], 25)
        self.assertEqual(attrs_buck["infrastructure"], "paved_shoulder")

        attrs_trail = get_accurate_road_attributes("James F. Hall Trail & Pomeroy Greenway", "Safest")
        self.assertEqual(attrs_trail["speed_limit_mph"], 15)
        self.assertEqual(attrs_trail["infrastructure"], "protected_bike_path")

    def test_time_of_day_traffic_factor_and_rush_hour(self) -> None:
        """Traffic factor must adapt during morning/evening commute hours vs mid-day and night."""
        from data_sources import get_time_of_day_traffic_factor, get_accurate_road_attributes
        tf_rush = get_time_of_day_traffic_factor("08:30 AM (Morning Peak Commute)")
        self.assertTrue(tf_rush["is_rush_hour"])
        self.assertGreater(tf_rush["multiplier"], 1.2)

        tf_mid = get_time_of_day_traffic_factor("12:00 PM (Mid-Day Standard Traffic)")
        self.assertFalse(tf_mid["is_rush_hour"])
        self.assertEqual(tf_mid["multiplier"], 1.0)

        # Arterial traffic must escalate to heavy during peak rush hour
        attrs_rush = get_accurate_road_attributes("Sunset Lake Road (DE 72)", "Balanced", time_factor=tf_rush)
        attrs_mid = get_accurate_road_attributes("Sunset Lake Road (DE 72)", "Balanced", time_factor=tf_mid)
        self.assertEqual(attrs_rush["traffic_exposure"], "heavy")
        self.assertEqual(attrs_mid["traffic_exposure"], "high")

    def test_planned_cycling_speed_duration(self) -> None:
        """Planned speed setting dynamically updates duration estimates in minutes."""
        from routing import package_single_osrm_route
        mock_route = {
            "distance": 16093.4,  # exactly 10 miles
            "duration": 3600,
            "geometry": {"coordinates": [[-75.747, 39.676], [-75.696, 39.571]]},
            "legs": [{"steps": [
                {
                    "name": "Sunset Lake Road (DE 72)",
                    "distance": 8000,
                    "duration": 1800,
                    "geometry": {"coordinates": [[-75.747, 39.676], [-75.72, 39.62]]},
                },
                {
                    "name": "Wrangle Hill Road (DE 72)",
                    "distance": 8093.4,
                    "duration": 1800,
                    "geometry": {"coordinates": [[-75.72, 39.62], [-75.696, 39.571]]},
                },
            ]}]
        }
        # 10 miles at 10 mph = 60 minutes
        r_10 = package_single_osrm_route(
            "Direct", mock_route, self.start, self.dest, "Start", "Dest", 16.09, planned_speed_mph=10.0
        )
        self.assertAlmostEqual(r_10.estimated_duration_mins, 60.0, delta=1.0)

        # 10 miles at 15 mph = 40 minutes
        r_15 = package_single_osrm_route(
            "Direct", mock_route, self.start, self.dest, "Start", "Dest", 16.09, planned_speed_mph=15.0
        )
        self.assertAlmostEqual(r_15.estimated_duration_mins, 40.0, delta=1.0)

        # 10 miles at 20 mph = 30 minutes
        r_20 = package_single_osrm_route(
            "Direct", mock_route, self.start, self.dest, "Start", "Dest", 16.09, planned_speed_mph=20.0
        )
        self.assertAlmostEqual(r_20.estimated_duration_mins, 30.0, delta=1.0)

    def test_schedule_calculation_and_type_safety(self) -> None:
        """Verifies start and end times calculation from typed inputs, and resilient float conversion."""
        import sys
        sys.path.insert(0, ".")
        from app import compute_trip_schedule, parse_speed_mph

        # Test speed parsing with various messy string inputs
        self.assertEqual(parse_speed_mph("12"), 12.0)
        self.assertEqual(parse_speed_mph("14.5 mph"), 14.5)
        self.assertEqual(parse_speed_mph("fast"), 12.0)
        self.assertEqual(parse_speed_mph(""), 12.0)
        self.assertEqual(parse_speed_mph(18.0), 18.0)

        # Test schedule computation
        # 8:30 AM + 46.6 mins = 9:16 AM
        start_fmt, end_fmt, summary = compute_trip_schedule("8:30 AM", 46.6)
        self.assertEqual(start_fmt, "8:30 AM")
        self.assertEqual(end_fmt, "9:16 AM")
        self.assertIn("8:30 AM → 9:16 AM", summary)

        # 5:15 PM + 30 mins = 5:45 PM
        start_fmt2, end_fmt2, _ = compute_trip_schedule("5:15 PM", 30.0)
        self.assertEqual(start_fmt2, "5:15 PM")
        self.assertEqual(end_fmt2, "5:45 PM")

        # 24-hr format "17:00" + 45 mins = 5:45 PM
        start_fmt3, end_fmt3, _ = compute_trip_schedule("17:00", 45.0)
        self.assertEqual(start_fmt3, "5:00 PM")
        self.assertEqual(end_fmt3, "5:45 PM")


class TestSavedRoutesPersistence(unittest.TestCase):
    """Tests for Saved Routes persistence, duplicate prevention, and GPX export."""

    def test_add_load_and_delete_saved_route(self) -> None:
        """Verify adding, updating, querying, and deleting saved routes."""
        from storage import (
            add_saved_route, load_saved_routes, delete_saved_route,
            is_route_saved, get_saved_route_by_id
        )

        test_gpx = "<gpx><trk><name>Test</name></trk></gpx>"
        item = add_saved_route(
            name="UD Campus to Newark Reservoir",
            start_label="Newark, DE",
            dest_label="Newark Reservoir, DE",
            route_type="Safest",
            distance_km=4.2,
            duration_mins=16.0,
            safety_score=89.0,
            gpx_content=test_gpx
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.name, "UD Campus to Newark Reservoir")
        self.assertTrue(is_route_saved("Newark, DE", "Newark Reservoir, DE", "Safest"))

        # Verify lookup
        fetched = get_saved_route_by_id(item.route_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "UD Campus to Newark Reservoir")

        # Verify duplicate update
        updated = add_saved_route(
            name="UD Campus to Newark Reservoir (Updated)",
            start_label="Newark, DE",
            dest_label="Newark Reservoir, DE",
            route_type="Safest",
            distance_km=4.2,
            duration_mins=15.5,
            safety_score=91.0,
            gpx_content=test_gpx
        )
        self.assertEqual(updated.route_id, item.route_id)
        self.assertEqual(updated.name, "UD Campus to Newark Reservoir (Updated)")

        # Verify delete
        delete_saved_route(item.route_id)
        self.assertIsNone(get_saved_route_by_id(item.route_id))
        self.assertFalse(is_route_saved("Newark, DE", "Newark Reservoir, DE", "Safest"))

    def test_beta_mode_gates_saved_routes_and_keeps_gpx_export(self) -> None:
        """Verify Beta Mode hides Saved Routes controls while keeping GPX export enabled."""
        import os
        from unittest.mock import patch
        os.environ["DRAFTER_SKIP"] = "true"
        import main

        sample_seg = main.RoadSegment(
            segment_id="seg_test_1",
            name="Pomeroy Rail Trail",
            coordinates=[main.Coordinate(39.676, -75.747), main.Coordinate(39.680, -75.742)],
            length_km=1.2,
            infrastructure="protected_bike_path",
            speed_limit_mph=0,
            traffic_exposure="very_low",
            crash_record=None,
            intersection_risk="low",
            safety_score=95.0,
            confidence="HIGH",
            risk_category="LOWER_RISK",
            positive_factors=["Protected greenway"],
            negative_factors=[],
            evidence_notes="Test corridor",
            safer_alternative=""
        )
        sample_route = main.RouteOption(
            route_type="Safest",
            total_distance_km=1.2,
            estimated_duration_mins=5.0,
            overall_safety_score=95.0,
            high_risk_segments_count=0,
            bike_infrastructure_percentage=100.0,
            major_intersections_count=0,
            warnings=[],
            segments=[sample_seg],
            turn_instructions=[],
            selection_rationale="Test safest route"
        )
        mock_routes = {"Safest": sample_route}

        s = main.State()
        self.assertFalse(s.beta_mode)

        with patch("main.get_routes_from_state", return_value=mock_routes):
            nav_off = str(main.render_navbar("planner", s.beta_mode, s))
            self.assertNotIn("Saved Routes", nav_off)
            self.assertNotIn("Save Route", nav_off)

            res_off = str(main.route_results_page(s))
            self.assertNotIn("Save Route to Favorites", res_off)
            self.assertNotIn("Beta Mode:", res_off)
            self.assertIn("Export GPX File", res_off)

            det_off = str(main.segment_details_page(s))
            self.assertNotIn("Save This Route to Favorites", det_off)
            self.assertNotIn("Beta Mode:", det_off)
            self.assertIn("Export GPX Track", det_off)

            # Toggle Beta Mode ON
            main.toggle_beta_mode(s)
            self.assertTrue(s.beta_mode)

            nav_on = str(main.render_navbar("planner", s.beta_mode, s))
            self.assertIn("Saved Routes", nav_on)
            self.assertIn("Save Route (Beta)", nav_on)

            res_on = str(main.route_results_page(s))
            self.assertIn("Save Route to Favorites (Beta)", res_on)
            self.assertIn("Export GPX File", res_on)

            det_on = str(main.segment_details_page(s))
            self.assertIn("Save This Route to Favorites (Beta)", det_on)
            self.assertIn("Export GPX Track", det_on)

            # Accessing Saved Routes page works in Beta Mode
            saved_pg = str(main.go_to_saved(s))
            self.assertIn("Saved Bicycle Routes", saved_pg)

            # Toggle Beta Mode back OFF while on Saved Routes returns to results
            res_after = str(main.toggle_beta_mode(s))
            self.assertFalse(s.beta_mode)
            self.assertIn("Route Options Comparison", res_after)


if __name__ == '__main__':
    unittest.main()


