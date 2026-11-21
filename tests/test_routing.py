"""tests/test_routing.py - Unit tests for geocoding, OSRM parsers, and GPX."""

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
from geocoding import geocode_address  # noqa: E402
from models import Coordinate  # noqa: E402
from routing import (  # noqa: E402
    build_segments_from_osrm_route,
    compute_trip_schedule,
    format_distance,
    format_duration_text,
    infer_osm_segment_attributes,
    parse_speed_mph,
    plan_bicycle_routes,
    recalibrate_routes_for_speed,
)
from storage import export_route_to_gpx  # noqa: E402


class TestRoutingAndGeocoding(unittest.TestCase):
    """Unit tests verifying geocoding, routing modes, speed, and GPX."""

    @classmethod
    def setUpClass(cls) -> None:
        """Silence verbose pass output while keeping bakery failure reports."""
        bakery_assertions.QUIET = True

    def test_delaware_corridor_produces_distinct_modes(self) -> None:
        """Delaware benchmark graph must yield 3 distinct ordered routes."""
        start_coord, start_label = geocode_address(
            "Louis Redding Hall, Newark, DE", allow_remote=False
        )
        dest_coord, dest_label = geocode_address(
            "Kirkwood, DE", allow_remote=False
        )
        self.assertTrue(assert_equal(start_coord is not None, True))
        self.assertTrue(assert_equal(dest_coord is not None, True))
        assert start_coord is not None and dest_coord is not None

        routes = plan_bicycle_routes(
            start_coord,
            dest_coord,
            start_label,
            dest_label,
            12.0,
            allow_remote=False,
        )
        self.assertTrue(
            assert_equal(sorted(routes.keys()), ["Balanced", "Direct", "Safest"])
        )
        self.assertTrue(
            assert_equal(
                routes["Safest"].overall_safety_score
                > routes["Balanced"].overall_safety_score,
                True,
            )
        )
        self.assertTrue(
            assert_equal(
                routes["Balanced"].overall_safety_score
                > routes["Direct"].overall_safety_score,
                True,
            )
        )
        self.assertTrue(
            assert_equal(
                routes["Direct"].total_distance_km
                < routes["Safest"].total_distance_km,
                True,
            )
        )
        self.assertTrue(
            assert_equal(routes["Direct"].high_risk_segments_count > 0, True)
        )
        self.assertTrue(assert_equal(len(routes["Direct"].warnings) > 0, True))

    def test_identical_endpoints_honestly_return_single_route(self) -> None:
        """Co-located endpoints must honestly return a single short route."""
        anchor = Coordinate(39.676456, -75.747050)
        routes = plan_bicycle_routes(
            anchor, anchor, "Newark", "Newark", allow_remote=False
        )
        self.assertTrue(assert_equal(len(routes), 1))
        self.assertTrue(assert_equal("Safest" in routes, True))

    def test_geocoding_handles_coordinates_and_invalid_inputs(self) -> None:
        """Geocoding must accept decimal coordinates and reject nonsense."""
        coord, label = geocode_address("39.6765, -75.7471", allow_remote=False)
        self.assertTrue(assert_equal(coord is not None, True))
        assert coord is not None
        self.assertTrue(assert_equal(round(coord.latitude, 4), 39.6765))
        self.assertTrue(assert_equal("39.6765" in label, True))

        bad_coord, bad_err = geocode_address(
            "NotARealPlaceXYZ99999", allow_remote=False
        )
        self.assertTrue(assert_equal(bad_coord, None))
        self.assertTrue(assert_equal("Could not resolve" in bad_err, True))

        empty_coord, empty_err = geocode_address("   ", allow_remote=False)
        self.assertTrue(assert_equal(empty_coord, None))
        self.assertTrue(assert_equal("non-empty" in empty_err, True))

    def test_speed_recalibration_and_formatting_consistency(self) -> None:
        """Higher cycling speed must reduce route duration consistently."""
        origin = Coordinate(40.7661, -73.9772)
        destination = Coordinate(40.7126, -74.0048)
        routes = plan_bicycle_routes(
            origin,
            destination,
            "Central Park",
            "Brooklyn Bridge",
            10.0,
            allow_remote=False,
        )
        faster_routes = recalibrate_routes_for_speed(routes, 20.0)
        self.assertTrue(
            assert_equal(
                faster_routes["Safest"].estimated_duration_mins
                < routes["Safest"].estimated_duration_mins,
                True,
            )
        )
        self.assertTrue(assert_equal(parse_speed_mph("invalid", 12.0), 12.0))
        self.assertTrue(assert_equal(parse_speed_mph(999.0), 28.0))
        self.assertTrue(assert_equal(format_duration_text(45), "45 min"))
        self.assertTrue(assert_equal(format_duration_text(75), "1 hr 15 min"))
        self.assertTrue(assert_equal(format_distance(10.0, "km"), "10.0 km"))
        self.assertTrue(assert_equal(format_distance(10.0, "mi"), "6.2 mi"))
        self.assertTrue(
            assert_equal(
                compute_trip_schedule("08:30", 45.0), ("8:30 AM", "9:15 AM")
            )
        )

    def test_osrm_segment_scoring_and_gpx_export(self) -> None:
        """OSRM street steps must score objectively and export valid GPX."""
        greenway_info = infer_osm_segment_attributes(
            "Hudson River Greenway", "cycling"
        )
        arterial_info = infer_osm_segment_attributes(
            "Pulaski Highway (US 40)", "driving"
        )
        bike_de72 = infer_osm_segment_attributes(
            "Wrangle Hill Road (DE 72)", "cycling"
        )
        car_de72 = infer_osm_segment_attributes(
            "Wrangle Hill Road (DE 72)", "driving"
        )
        self.assertTrue(assert_equal(greenway_info[0], "protected_bike_path"))
        self.assertTrue(assert_equal(arterial_info[0], "none"))
        self.assertTrue(assert_equal(bike_de72, car_de72))

        mock_osrm = {
            "legs": [
                {
                    "steps": [
                        {
                            "name": "Hudson River Greenway",
                            "mode": "cycling",
                            "distance": 1500.0,
                            "geometry": {
                                "coordinates": [
                                    [-73.9862, 40.7812],
                                    [-73.9950, 40.7650],
                                    [-74.0080, 40.7420],
                                ]
                            },
                        }
                    ]
                }
            ]
        }
        segments = build_segments_from_osrm_route(mock_osrm, "osm_safe")
        self.assertTrue(assert_equal(len(segments), 1))
        self.assertTrue(assert_equal(segments[0].risk_category, "LOWER_RISK"))

        origin = Coordinate(39.676456, -75.747050)
        destination = Coordinate(39.571807, -75.696079)
        routes = plan_bicycle_routes(
            origin, destination, "Newark, DE", "Kirkwood, DE", allow_remote=False
        )
        gpx_xml = export_route_to_gpx(
            routes["Safest"], "Newark, DE", "Kirkwood, DE"
        )
        self.assertTrue(assert_equal('<gpx version="1.1"' in gpx_xml, True))
        self.assertTrue(assert_equal("<trkpt" in gpx_xml, True))


if __name__ == "__main__":
    unittest.main()
