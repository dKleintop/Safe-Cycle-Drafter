"""tests/test_drafter_routes.py - Drafter @route & State transition tests."""

import os
import sys
import unittest

os.environ["DRAFTER_SKIP"] = "1"
os.environ["DRAFTER_OFFLINE_TESTS"] = "1"
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR: str = os.path.join(BASE_DIR, ".py311_packages")
if os.path.exists(PKG_DIR) and PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bakery import assert_equal  # noqa: E402
import bakery.assertions as bakery_assertions  # noqa: E402
from drafter import (  # noqa: E402
    Page,
    get_main_server,
    get_site_information,
)
import main  # noqa: E402


class TestDrafterRoutes(unittest.TestCase):
    """End-to-end tests for SafeCycle Drafter routes and State mutations."""

    @classmethod
    def setUpClass(cls) -> None:
        """Silence verbose pass output while keeping bakery failure reports."""
        bakery_assertions.QUIET = True

    def test_site_information_and_route_count(self) -> None:
        """Verify set_site_information and at least 10 registered routes."""
        server = get_main_server()
        self.assertTrue(assert_equal(len(server.router.routes) >= 10, True))
        site_info = get_site_information()
        self.assertTrue(assert_equal(bool(site_info), True))

    def test_all_five_pages_render_pure_drafter_pages(self) -> None:
        """Verify all 5 page @routes return valid Drafter Page objects."""
        session_state = main.State()
        for page_handler in (
            main.index,
            main.route_results_page,
            main.segment_details_page,
            main.settings_page,
            main.about_page,
        ):
            rendered_page = page_handler(session_state)
            self.assertTrue(assert_equal(isinstance(rendered_page, Page), True))

    def test_full_user_journeys_update_state(self) -> None:
        """Verify key user flows meaningfully modify multiple State fields."""
        session_state = main.State()

        result_page = main.handle_generate_route(
            session_state,
            start_address="Louis Redding Hall, Newark, DE",
            dest_address="Kirkwood, DE",
            preferred_mode="Balanced",
            planned_speed="15.0",
        )
        self.assertTrue(assert_equal(isinstance(result_page, Page), True))
        self.assertTrue(assert_equal(session_state.active_route_type, "Balanced"))
        self.assertTrue(assert_equal(session_state.planned_speed, 15.0))

        invalid_page = main.handle_generate_route(
            session_state,
            start_address="NotARealPlaceXYZ99999",
            dest_address="Kirkwood, DE",
        )
        self.assertTrue(assert_equal(isinstance(invalid_page, Page), True))
        self.assertTrue(assert_equal(session_state.current_page, "planner"))

        session_state.start_address = "Louis Redding Hall, Newark, DE"
        main.handle_swap_endpoints(session_state)
        self.assertTrue(
            assert_equal(session_state.start_address, "Kirkwood, DE")
        )
        main.handle_swap_endpoints(session_state)
        self.assertTrue(
            assert_equal(
                session_state.start_address, "Louis Redding Hall, Newark, DE"
            )
        )

        main.select_route_mode(session_state, route_type="Direct")
        self.assertTrue(assert_equal(session_state.active_route_type, "Direct"))
        main.inspect_segment(session_state, segment_id="de_dir_1")
        self.assertTrue(
            assert_equal(session_state.selected_segment_id, "de_dir_1")
        )
        self.assertTrue(assert_equal(session_state.current_page, "segment"))

        session_state.dark_mode = False
        main.handle_toggle_dark_mode(session_state)
        self.assertTrue(assert_equal(session_state.dark_mode, True))
        main.handle_toggle_dark_mode(session_state)
        self.assertTrue(assert_equal(session_state.dark_mode, False))

        session_state.show_advanced = False
        main.handle_toggle_advanced(session_state)
        self.assertTrue(assert_equal(session_state.show_advanced, True))
        main.handle_toggle_advanced(session_state)
        self.assertTrue(assert_equal(session_state.show_advanced, False))

        main.handle_save_settings(
            session_state,
            planned_speed="14.5",
            start_time="17:15",
            preferred_mode="Safest",
            units="km",
            show_advanced=True,
            dark_mode=True,
        )
        self.assertTrue(assert_equal(session_state.current_page, "planner"))
        self.assertTrue(assert_equal(session_state.units, "km"))
        self.assertTrue(assert_equal(session_state.show_advanced, True))
        self.assertTrue(assert_equal(session_state.dark_mode, True))
        self.assertTrue(
            assert_equal(len(session_state.route_summaries), 3)
        )


if __name__ == "__main__":
    unittest.main()
