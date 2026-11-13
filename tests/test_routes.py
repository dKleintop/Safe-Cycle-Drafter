"""
tests/test_routes.py - Unit tests covering all 37 Drafter @route functions in main.py
"""
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ["DRAFTER_SKIP"] = "true"
import data_sources  # noqa: E402, F401
import geocoding  # noqa: E402, F401
import models  # noqa: E402, F401
import routing  # noqa: E402, F401
import safety  # noqa: E402, F401
import storage  # noqa: E402, F401
import main  # noqa: E402


class TestAllDrafterRoutes(unittest.TestCase):
    """Comprehensive unittest suite exercising every @route handler and State mutation."""

    def setUp(self) -> None:
        """Create an isolated temporary directory for saved routes storage."""
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_saved_file = os.path.join(self.tmp_dir.name, "saved_routes.json")

    def tearDown(self) -> None:
        """Clean up temporary saved routes directory after each test."""
        self.tmp_dir.cleanup()

    def test_planner_and_preset_routes(self) -> None:
        """Test index, go_to_planner, go_to_about, and all 6 preset @route handlers."""
        with (
            patch.object(main, "fetch_osrm_bike_routes", return_value=[]),
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
        ):
            st = main.State()
            pg = main.index(st)
            self.assertEqual(st.current_page, "planner")
            self.assertIn("Plan a Safer Bicycle Route", str(pg))

            self.assertIn("Central Park South", str(main.pick_preset_nyc(st)))
            self.assertEqual(st.start_address, "Central Park South, New York, NY")

            main.pick_preset_sf(st)
            self.assertEqual(st.dest_address, "Golden Gate Park Panhandle, San Francisco, CA")

            main.pick_preset_greenway(st)
            self.assertIn("Greenway", st.start_address)

            main.pick_preset_seattle(st)
            self.assertIn("Seattle", st.start_address)

            main.pick_preset_portland(st)
            self.assertIn("Portland", st.start_address)

            main.pick_preset_newark(st)
            self.assertEqual(st.dest_address, "Kirkwood, DE")

            main.go_to_planner(st)
            self.assertEqual(st.current_page, "planner")

            main.go_to_about(st)
            self.assertEqual(st.current_page, "about")

    def test_route_generation_selection_timing_and_details(self) -> None:
        """Test route generation, results page, mode switches, timing, and segment inspection."""
        with (
            patch.object(main, "fetch_osrm_bike_routes", return_value=[]),
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
        ):
            st = main.State()
            pg = main.handle_generate_route(
                st,
                start_address="Louis Redding Hall, Newark, DE",
                dest_address="Kirkwood, DE",
                preferred_mode="Balanced",
                max_risk_tolerance="low",
                detour_tolerance="35%",
                time_hhmm="08:45",
                time_ampm="AM",
                planned_speed="15",
            )
            self.assertEqual(st.current_page, "results")
            self.assertEqual(st.preferred_mode, "Balanced")
            self.assertEqual(st.max_risk_tolerance, "low")
            self.assertEqual(st.detour_tolerance, "35%")
            self.assertEqual(st.departure_time, "08:45 AM")
            self.assertEqual(st.planned_speed_mph, "15.0")
            self.assertIn("Route Options Comparison", str(pg))

            main.update_results_timing(st, time_hhmm="05:15", time_ampm="PM", planned_speed="16")
            self.assertEqual(st.departure_time, "05:15 PM")
            self.assertEqual(st.planned_speed_mph, "16.0")

            main.select_safest_mode(st)
            self.assertEqual(st.active_route_type, "Safest")
            main.select_balanced_mode(st)
            self.assertEqual(st.active_route_type, "Balanced")
            main.select_direct_mode(st)
            self.assertEqual(st.active_route_type, "Direct")
            main.select_custom_mode(st, "Safest")
            self.assertEqual(st.active_route_type, "Safest")

            main.go_to_results(st)
            self.assertEqual(st.current_page, "results")

            routes = main.get_routes_from_state(st)
            seg_id = routes["Safest"].segments[0].segment_id
            det_pg = main.inspect_segment(st, seg_id)
            self.assertEqual(st.selected_segment_id, seg_id)
            self.assertEqual(st.current_page, "details")
            self.assertIn("Safety Score", str(det_pg))

            self.assertEqual(main.segment_details_page(st).__class__.__name__, "Page")

            main.handle_export_gpx(st)
            main.export_specific_gpx(st, "Direct")
            self.assertEqual(st.active_route_type, "Direct")

    def test_navigation_beta_saved_routes_and_hazard_loop(self) -> None:
        """Test Beta gating, navigation stepping, saved route CRUD, and HazardReport list loop."""
        with (
            patch.object(main, "fetch_osrm_bike_routes", return_value=[]),
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
            patch.object(main, "SAVED_ROUTES_FILE", self.tmp_saved_file),
        ):
            st = main.State()

            # Beta off blocks go_to_navigation and go_to_saved
            main.go_to_navigation(st)
            self.assertEqual(st.current_page, "results")
            main.go_to_saved(st)
            self.assertEqual(st.current_page, "results")

            # Toggle Beta Mode on
            main.toggle_beta_mode(st)
            self.assertTrue(st.beta_mode)

            # Navigation routes
            nav_pg = main.start_route_navigation(st, "Safest")
            self.assertEqual(st.current_page, "navigation")
            self.assertEqual(st.nav_step, 1)
            self.assertIn("Navigation", str(nav_pg))

            main.navigation_page(st)
            main.handle_next_nav_step(st)
            main.handle_prev_nav_step(st)
            main.handle_recalculate_route(st)
            self.assertEqual(st.nav_step, 1)
            self.assertIn("recalculated", st.nav_status.lower())

            # Saved routes CRUD handlers
            main.go_to_saved(st)
            self.assertEqual(st.current_page, "saved")
            st.start_address = "Market St at 4th St, San Francisco, CA"
            st.dest_address = "Golden Gate Park Panhandle, San Francisco, CA"
            initial_count = len(main.load_saved_routes())
            main.handle_save_current_route(st, "Morning Commute")
            main.save_specific_route(st, "Balanced")
            saved_list = main.load_saved_routes()
            self.assertEqual(len(saved_list), initial_count + 2)

            rid = saved_list[-1].route_id
            main.export_saved_route(st, rid)
            main.load_saved_route(st, rid)
            self.assertEqual(st.current_page, "results")

            main.delete_saved_route_handler(st, rid)
            self.assertEqual(len(main.load_saved_routes()), initial_count + 1)
            main.saved_routes_page(st)

            # HazardReport list modification and loop rendering on about_page
            about_pg = main.handle_submit_hazard(st, "Elkton Rd & Amstel Ave", "Missing curb cut")
            self.assertEqual(len(st.reported_hazards), 1)
            self.assertEqual(st.reported_hazards[0].road, "Elkton Rd & Amstel Ave")
            about_html = str(about_pg)
            self.assertIn("Elkton Rd & Amstel Ave", about_html)
            self.assertIn("Missing curb cut", about_html)
            self.assertEqual(main.about_page(st).__class__.__name__, "Page")

            # Toggle Beta Mode back off
            main.toggle_beta_mode(st)
            self.assertFalse(st.beta_mode)


if __name__ == "__main__":
    unittest.main()
