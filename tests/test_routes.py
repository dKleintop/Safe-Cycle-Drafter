"""
tests/test_routes.py - Unit tests covering all 38 Drafter @route functions in main.py
"""
import os
import re
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

            # Basic mode default hides safety breakdown, spectrum, crash records, and diagnostics
            self.assertFalse(st.advanced_mode)
            res_basic_html = str(main.route_results_page(st))
            self.assertIn("Route Options Comparison", res_basic_html)
            self.assertIn("Advanced Mode", res_basic_html)
            self.assertNotIn("Safety Corridor Spectrum", res_basic_html)
            self.assertNotIn("Road Corridor Safety Breakdown", res_basic_html)
            self.assertNotIn("Key Streets Along Your Route", res_basic_html)
            self.assertNotIn("Route Evaluation & Routing Diagnostics", res_basic_html)

            det_basic_html = str(main.segment_details_page(st))
            self.assertEqual(st.current_page, "details")
            self.assertNotIn("Official Crash Records", det_basic_html)

            # Toggle Advanced Mode ON from Details page shows Official Crash Records & stays on Details
            det_adv_html = str(main.toggle_advanced_mode(st))
            self.assertTrue(st.advanced_mode)
            self.assertEqual(st.current_page, "details")
            self.assertIn("Official Crash Records", det_adv_html)

            # Results page in Advanced Mode shows full telemetry, but keeps Diagnostics hidden when Beta OFF
            res_adv_html = str(main.route_results_page(st))
            self.assertIn("Basic View", res_adv_html)
            self.assertIn("Safety Corridor Spectrum", res_adv_html)
            self.assertIn("Road Corridor Safety Breakdown", res_adv_html)
            self.assertNotIn("Route Evaluation & Routing Diagnostics", res_adv_html)

            # Toggle Advanced Mode OFF returns to Basic Mode on Results page
            res_back_basic = str(main.toggle_advanced_mode(st))
            self.assertFalse(st.advanced_mode)
            self.assertEqual(st.current_page, "results")
            self.assertNotIn("Safety Corridor Spectrum", res_back_basic)
            self.assertNotIn("Road Corridor Safety Breakdown", res_back_basic)

            export_pg_html = str(main.handle_export_gpx(st))
            self.assertIn('data-auto-gpx="true"', export_pg_html)
            self.assertIn("safecycle_safest_route.gpx", export_pg_html)
            main.export_specific_gpx(st, "Direct")
            self.assertEqual(st.active_route_type, "Direct")

            # Bike-themed loading overlay variations & non-mutating fast speed recalibration
            for tok in (
                "safecycle_loading_overlay",
                "safecycleShowLoader",
                "LOADER_VARIANTS",
                "greenway",
                "radar",
                "climb",
                "night",
                "gpx",
                "safecycleSelectLoaderVariant",
            ):
                self.assertIn(tok, main.THEME_AND_DOWNLOAD_JS)
            orig_dur = routes["Safest"].estimated_duration_mins
            recal = main.recalibrate_routes_for_speed(routes, 20.0)
            self.assertLessEqual(recal["Safest"].estimated_duration_mins, orig_dur)
            self.assertEqual(routes["Safest"].estimated_duration_mins, orig_dur)

            # Dark mode toggle preserves current page and toggles theme marker
            dark_pg_html = str(main.toggle_dark_mode(st))
            self.assertTrue(st.dark_mode)
            self.assertIn('data-safecycle-theme="dark"', dark_pg_html)
            self.assertEqual(st.current_page, "results")
            light_pg_html = str(main.toggle_dark_mode(st))
            self.assertFalse(st.dark_mode)
            self.assertIn('data-safecycle-theme="light"', light_pg_html)

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

            # Toggle Beta Mode on -> Diagnostics and Beta pages become visible
            main.toggle_beta_mode(st)
            self.assertTrue(st.beta_mode)
            res_beta_html = str(main.route_results_page(st))
            self.assertIn("Route Evaluation & Routing Diagnostics", res_beta_html)

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
            saved_export_html = str(main.export_saved_route(st, rid))
            self.assertIn('data-auto-gpx="true"', saved_export_html)
            main.load_saved_route(st, rid)
            self.assertEqual(st.current_page, "results")

            main.delete_saved_route_handler(st, rid)
            self.assertEqual(len(main.load_saved_routes()), initial_count + 1)
            main.saved_routes_page(st)

            # HazardReport list modification and loop rendering on about_page (Beta Mode)
            about_pg = main.handle_submit_hazard(st, "Elkton Rd & Amstel Ave", "Missing curb cut")
            self.assertEqual(len(st.reported_hazards), 1)
            self.assertEqual(st.reported_hazards[0].road, "Elkton Rd & Amstel Ave")
            about_html = str(about_pg)
            self.assertIn("Elkton Rd & Amstel Ave", about_html)
            self.assertIn("Missing curb cut", about_html)
            self.assertEqual(main.about_page(st).__class__.__name__, "Page")

            # Dark mode toggle on about page
            about_dark_html = str(main.toggle_dark_mode(st))
            self.assertTrue(st.dark_mode)
            self.assertIn('data-safecycle-theme="dark"', about_dark_html)
            main.toggle_dark_mode(st)
            self.assertFalse(st.dark_mode)

            # Toggle Beta Mode back off and confirm hazard reporting is hidden & gated
            main.toggle_beta_mode(st)
            self.assertFalse(st.beta_mode)
            about_standard_html = str(main.about_page(st))
            self.assertNotIn("Report a Road Hazard", about_standard_html)
            main.handle_submit_hazard(st, "Main St", "Ignored while Beta off")
            self.assertEqual(len(st.reported_hazards), 1)

    def test_formatting_helpers_and_map_descriptions(self) -> None:
        """Verify hours:mins duration formatting (>60 mins), thousands commas, and no map descriptions."""
        self.assertEqual(main.format_duration_parts(45.0), ("45", "min"))
        self.assertEqual(main.format_duration_parts(60.0), ("60", "min"))
        self.assertEqual(main.format_duration_parts(61.0), ("1:01", "hr"))
        self.assertEqual(main.format_duration_parts(125.0), ("2:05", "hrs"))
        self.assertEqual(main.format_duration_text(185.0), "3:05 hrs")

        self.assertEqual(main.format_number(999.0, 0), "999")
        self.assertEqual(main.format_number(1000.0, 0), "1,000")
        self.assertEqual(main.format_number(1234.56, 1), "1,234.6")

        long_seg = main.RoadSegment(
            segment_id="long_1",
            name="Long Corridor",
            length_km=2012.3,
            infrastructure="protected_bike_path",
            speed_limit_mph=20,
            traffic_exposure="low",
            intersection_risk="low",
            crash_record=main.CrashRecord(total_crashes=0),
            coordinates=[main.Coordinate(40.76, -73.98), main.Coordinate(40.77, -73.97)],
        )
        long_route = main.RouteOption(
            route_type="Safest",
            segments=[long_seg],
            total_distance_km=2012.3,
            estimated_duration_mins=125.0,
            overall_safety_score=92.0,
            bike_infrastructure_percentage=100.0,
            high_risk_segments_count=0,
            major_intersections_count=2,
            warnings=[],
            selection_rationale="Long distance test",
            turn_instructions=[],
            elevation_gain_m=1500.0,
        )
        basic_card_html = str(main.render_strava_route_card(long_route, "Safest", True, advanced_mode=False))
        self.assertIn("2:05", basic_card_html)
        self.assertIn("hrs", basic_card_html)
        self.assertIn("1,250.4", basic_card_html)

        adv_card_html = str(main.render_strava_route_card(long_route, "Safest", True, advanced_mode=True))
        self.assertIn("2:05", adv_card_html)
        self.assertIn("1,250.4", adv_card_html)
        self.assertIn("2,012.3", adv_card_html)
        self.assertIn("4,921", adv_card_html)
        self.assertIn("1,500", adv_card_html)

        with (
            patch.object(main, "fetch_osrm_bike_routes", return_value=[]),
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
        ):
            st = main.State()
            planner_html = str(main.index(st))
            self.assertNotIn(
                "Interactive OpenStreetMap bicycle map showing start and destination coordinates.",
                planner_html,
            )
            results_html = str(main.handle_generate_route(st))
            self.assertNotIn(
                "Interactive route map showing selected and possible cycling paths",
                results_html,
            )

    def test_ui_overhaul_layout_zero_emojis_and_clean_copy(self) -> None:
        """Verify split single-overview results layout, trimmed helper copy, and zero emojis."""
        emoji_re = re.compile(
            r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u23E9-\u23FA\u2B50\u2B55]"
        )
        with (
            patch.object(main, "fetch_osrm_bike_routes", return_value=[]),
            patch("urllib.request.urlopen", side_effect=OSError("offline test")),
            patch.object(main, "SAVED_ROUTES_FILE", self.tmp_saved_file),
        ):
            st = main.State()
            planner_html = str(main.index(st))
            for stale_copy in (
                "Street address, trail trailhead",
                "Destination address, park, landmark",
                "Auto-formats to 00:00",
                "Type cycling pace in mph",
            ):
                self.assertNotIn(stale_copy, planner_html)
            self.assertIn("sc-planner-grid", planner_html)
            self.assertEqual(emoji_re.findall(planner_html), [])

            # Basic view results: split map + single overview slot active
            res_basic = str(main.handle_generate_route(st))
            self.assertIn("sc-results-split", res_basic)
            self.assertIn("sc-overview-panel", res_basic)
            self.assertIn("sc-switch-tabs", res_basic)
            flex_count = res_basic.count('class="sc-overview-slot" style="display: flex;"')
            none_count = res_basic.count('class="sc-overview-slot" style="display: none;"')
            self.assertEqual(flex_count, 1)
            self.assertGreaterEqual(none_count, 2)
            self.assertEqual(emoji_re.findall(res_basic), [])

            # Switching active route moves display: flex to that slot only
            main.select_balanced_mode(st)
            res_balanced = str(main.route_results_page(st))
            self.assertEqual(
                res_balanced.count('class="sc-overview-slot" style="display: flex;"'),
                1,
            )
            self.assertIn(
                'id="route_overview_slot_Balanced" class="sc-overview-slot" style="display: flex;"',
                res_balanced,
            )
            self.assertIn(
                'id="route_overview_slot_Safest" class="sc-overview-slot" style="display: none;"',
                res_balanced,
            )

            # Advanced + Beta modes and secondary pages contain zero emojis & trimmed helper text
            main.toggle_advanced_mode(st)
            main.toggle_beta_mode(st)
            res_adv_beta = str(main.route_results_page(st))
            self.assertNotIn("00:00 format", res_adv_beta)
            self.assertNotIn("e.g. 12.0 or 15", res_adv_beta)
            self.assertEqual(emoji_re.findall(res_adv_beta), [])

            routes = main.get_routes_from_state(st)
            seg_id = routes["Balanced"].segments[0].segment_id
            for page_html in (
                str(main.inspect_segment(st, seg_id)),
                str(main.start_route_navigation(st, "Balanced")),
                str(main.go_to_saved(st)),
                str(main.go_to_about(st)),
            ):
                self.assertEqual(emoji_re.findall(page_html), [])


if __name__ == "__main__":
    unittest.main()
