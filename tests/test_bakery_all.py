"""tests/test_bakery_all.py - Complete bakery assert_equal unit test suite.

Verifies every testable function across models.py, safety.py, geocoding.py,
routing.py, storage.py, visuals.py, and main.py (all helpers and @routes)
using `from bakery import assert_equal`.
"""

import json
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

from bakery import assert_equal, student_tests  # noqa: E402
import bakery.assertions as bakery_assertions  # noqa: E402
import geocoding  # noqa: E402
import main  # noqa: E402
from models import Coordinate, CrashRecord  # noqa: E402
import routing  # noqa: E402
import safety  # noqa: E402
import storage  # noqa: E402
import visuals  # noqa: E402


class TestAllModulesWithBakery(unittest.TestCase):
    """Comprehensive bakery assert_equal tests for every testable function."""

    @classmethod
    def setUpClass(cls) -> None:
        """Silence verbose pass output while keeping bakery failure reports."""
        bakery_assertions.QUIET = True

    def test_models_and_safety_helpers(self) -> None:
        """Verify Coordinate.to_tuple and all safety.py functions."""
        coord = Coordinate(39.6765, -75.7471)
        self.assertTrue(assert_equal(coord.to_tuple(), (39.6765, -75.7471)))

        self.assertTrue(
            assert_equal(
                safety.determine_risk_category(88.0, "HIGH"), "LOWER_RISK"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.determine_risk_category(64.0, "MEDIUM"), "MODERATE"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.determine_risk_category(48.0, "HIGH"), "ELEVATED"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.determine_risk_category(22.0, "HIGH"), "HIGH_RISK"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.determine_risk_category(90.0, "INSUFFICIENT"), "UNKNOWN"
            )
        )
        self.assertTrue(
            assert_equal(safety.get_risk_color_hex("LOWER_RISK"), "#15803d")
        )
        self.assertTrue(
            assert_equal(
                safety.get_risk_label("HIGH_RISK"), "High Risk (<40)"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.format_infrastructure_label("painted_lane"),
                "Painted Bicycle Lane",
            )
        )
        self.assertTrue(
            assert_equal(safety.compute_speed_score(20), (90.0, True))
        )
        self.assertTrue(
            assert_equal(safety.compute_speed_score(None), (40.0, False))
        )
        self.assertTrue(
            assert_equal(safety.compute_crash_score(None), (50.0, False))
        )
        self.assertTrue(
            assert_equal(
                safety.compute_crash_score(CrashRecord(0, 0, 0)), (82.0, True)
            )
        )

        infra_score, infra_known, infra_pos, infra_neg = (
            safety.score_infrastructure_factor("protected_bike_path")
        )
        self.assertTrue(assert_equal(infra_score, 100.0))
        self.assertTrue(assert_equal(infra_known, True))
        self.assertTrue(assert_equal(len(infra_pos), 1))
        self.assertTrue(assert_equal(len(infra_neg), 0))

        traffic_score, traffic_known, traffic_pos, _ = (
            safety.score_traffic_factor("low")
        )
        self.assertTrue(assert_equal(traffic_score, 82.0))
        self.assertTrue(assert_equal(traffic_known, True))
        self.assertTrue(assert_equal(len(traffic_pos), 1))

        inter_score, inter_known, _, inter_neg = (
            safety.score_intersection_factor("high_conflict")
        )
        self.assertTrue(assert_equal(inter_score, 20.0))
        self.assertTrue(assert_equal(inter_known, True))
        self.assertTrue(assert_equal(len(inter_neg), 1))

        self.assertTrue(
            assert_equal(
                safety.compute_confidence_level(5, True, True), "HIGH"
            )
        )
        self.assertTrue(
            assert_equal(
                safety.compute_confidence_level(1, False, False),
                "INSUFFICIENT",
            )
        )

        score, category, confidence, _, _, _ = safety.evaluate_road_safety(
            "protected_bike_path",
            15,
            "very_low",
            CrashRecord(0, 0, 0),
            "low",
        )
        self.assertTrue(assert_equal(category, "LOWER_RISK"))
        self.assertTrue(assert_equal(confidence, "HIGH"))
        self.assertTrue(assert_equal(score > 90.0, True))

    def test_geocoding_helpers(self) -> None:
        """Verify parse_coordinate_pair and geocode_address in geocoding.py."""
        parsed = geocoding.parse_coordinate_pair("39.6765, -75.7471")
        self.assertTrue(assert_equal(parsed is not None, True))
        assert parsed is not None
        self.assertTrue(assert_equal(parsed.latitude, 39.6765))
        self.assertTrue(
            assert_equal(geocoding.parse_coordinate_pair("bad_input"), None)
        )

        coord, label = geocoding.geocode_address(
            "Kirkwood, DE", allow_remote=False
        )
        self.assertTrue(assert_equal(coord is not None, True))
        self.assertTrue(assert_equal(label, "Kirkwood, DE"))
        missing_coord, _ = geocoding.geocode_address("   ", allow_remote=False)
        self.assertTrue(assert_equal(missing_coord, None))

        suggestions = geocoding.search_location_suggestions("Newark", limit=4)
        self.assertTrue(assert_equal(len(suggestions) >= 1, True))
        self.assertTrue(assert_equal("Newark" in suggestions[0]["name"], True))
        catalog_items = json.loads(geocoding.build_location_catalog_json())
        self.assertTrue(assert_equal(len(catalog_items) >= 10, True))

    def test_routing_graph_osrm_parsers_and_helpers(self) -> None:
        """Verify every testable function and graph method in routing.py."""
        origin = Coordinate(39.676456, -75.747050)
        destination = Coordinate(39.571807, -75.696079)
        distance_km = routing.calculate_haversine_distance_km(
            origin, destination
        )
        self.assertTrue(assert_equal(round(distance_km, 1), 12.4))
        self.assertTrue(assert_equal(routing.parse_speed_mph("14.5"), 14.5))
        self.assertTrue(assert_equal(routing.parse_speed_mph("bad", 12.0), 12.0))
        self.assertTrue(assert_equal(routing.parse_detour_ratio("50%"), 1.5))

        morning_note, morning_mult = routing.get_time_of_day_traffic_note(
            "08:00"
        )
        self.assertTrue(assert_equal("Morning" in morning_note, True))
        self.assertTrue(assert_equal(morning_mult, 1.15))

        self.assertTrue(
            assert_equal(
                routing.compute_trip_schedule("08:30", 45.0),
                ("8:30 AM", "9:15 AM"),
            )
        )
        self.assertTrue(
            assert_equal(routing.format_duration_text(75.0), "1 hr 15 min")
        )
        self.assertTrue(
            assert_equal(routing.format_distance(10.0, "km"), "10.0 km")
        )

        segment = routing.make_evaluated_segment(
            "seg_1",
            "Campus Greenway",
            [origin, destination],
            2.5,
            "protected_bike_path",
            15,
            "very_low",
            CrashRecord(0, 0, 0),
            "low",
        )
        self.assertTrue(assert_equal(segment.risk_category, "LOWER_RISK"))

        many_coords = [
            Coordinate(39.60 + i * 0.001, -75.70) for i in range(60)
        ]
        sampled = routing.downsample_coordinates(many_coords, max_points=10)
        self.assertTrue(assert_equal(len(sampled), 10))
        self.assertTrue(assert_equal(sampled[0], many_coords[0]))
        self.assertTrue(assert_equal(sampled[-1], many_coords[-1]))

        self.assertTrue(
            assert_equal(
                routing.normalize_street_key("Capitol Trail (DE 72)"),
                "capitol trail",
            )
        )
        self.assertTrue(
            assert_equal(
                routing.contains_any_word_phrase(
                    "Pleasant Valley Road", routing.QUIET_STREET_KEYWORDS
                ),
                False,
            )
        )
        self.assertTrue(
            assert_equal(
                routing.contains_any_word_phrase(
                    "Scholar Drive", routing.QUIET_STREET_KEYWORDS
                ),
                True,
            )
        )

        trail_attr = routing.infer_osm_segment_attributes(
            "Pomeroy Trail", "cycling"
        )
        self.assertTrue(assert_equal(trail_attr[0], "protected_bike_path"))
        capitol_attr = routing.infer_osm_segment_attributes(
            "Capitol Trail (DE 72)", "cycling"
        )
        self.assertTrue(assert_equal(capitol_attr[0], "shared_lane"))
        self.assertTrue(assert_equal(capitol_attr[1], 35))
        hwy_attr = routing.infer_osm_segment_attributes(
            "Pulaski Highway (US 40)", "driving"
        )
        self.assertTrue(assert_equal(hwy_attr[0], "none"))
        self.assertTrue(assert_equal(hwy_attr[1], 45))
        mway_attr = routing.infer_osm_segment_attributes(
            "Connector", "driving", ("motorway",)
        )
        self.assertTrue(assert_equal(mway_attr[1], 55))

        sample_osrm_route = {
            "legs": [
                {
                    "steps": [
                        {
                            "name": "Pomeroy Trail",
                            "ref": "",
                            "mode": "cycling",
                            "distance": 1200.0,
                            "geometry": {
                                "coordinates": [
                                    [-75.7470, 39.6764],
                                    [-75.7410, 39.6650],
                                ]
                            },
                        },
                        {
                            "name": "South Chapel Street",
                            "ref": "DE 72",
                            "mode": "cycling",
                            "distance": 850.0,
                            "geometry": {
                                "coordinates": [
                                    [-75.7410, 39.6650],
                                    [-75.7350, 39.6550],
                                ]
                            },
                        },
                    ]
                }
            ]
        }
        osrm_segments = routing.build_segments_from_osrm_route(
            sample_osrm_route, "osm_safe"
        )
        self.assertTrue(assert_equal(len(osrm_segments), 2))
        self.assertTrue(assert_equal(osrm_segments[0].name, "Pomeroy Trail"))

        via_pt = routing.compute_via_waypoint(origin, destination, 0.16)
        self.assertTrue(assert_equal(isinstance(via_pt, Coordinate), True))
        self.assertTrue(
            assert_equal(
                round(routing.score_segments_weighted([segment]), 1),
                round(segment.safety_score, 1),
            )
        )
        self.assertTrue(assert_equal(routing.score_segments_weighted([]), 0.0))

        spur_segs = [
            routing.make_evaluated_segment(
                "sp1",
                "Jaymar Boulevard",
                [origin, Coordinate(39.65, -75.73)],
                0.8,
                "shared_lane",
                25,
                "low",
                None,
                "low",
            ),
            routing.make_evaluated_segment(
                "sp2",
                "Warren Drive",
                [Coordinate(39.65, -75.73), Coordinate(39.648, -75.728)],
                0.4,
                "traffic_calmed_street",
                20,
                "low",
                None,
                "low",
            ),
            routing.make_evaluated_segment(
                "sp3",
                "Jaymar Boulevard",
                [Coordinate(39.648, -75.728), destination],
                0.8,
                "shared_lane",
                25,
                "low",
                None,
                "low",
            ),
        ]
        self.assertTrue(assert_equal(routing.has_backtrack_loop(spur_segs), True))
        self.assertTrue(assert_equal(routing.has_backtrack_loop([segment]), False))

        flat_pts = routing.flatten_route_coords(osrm_segments)
        self.assertTrue(assert_equal(len(flat_pts), 3))
        self.assertTrue(
            assert_equal(
                routing.compute_route_overlap_ratio(
                    osrm_segments, osrm_segments
                ),
                1.0,
            )
        )
        self.assertTrue(
            assert_equal(
                routing.compute_corridor_separation_km(
                    osrm_segments, osrm_segments
                ),
                0.0,
            )
        )
        self.assertTrue(
            assert_equal(
                routing.are_routes_similar(osrm_segments, osrm_segments, 5.0),
                True,
            )
        )
        retagged = routing.retag_route_segments(osrm_segments, "test")
        self.assertTrue(assert_equal(retagged[0].segment_id, "test_1"))

        alt_segs = routing.build_generic_safest_segments(
            origin, destination, "Start", "End", 0.025, 12.0
        )
        dir_only = routing.build_generic_direct_segments(
            origin, destination, "Start", "End", 12.0
        )
        ranked = routing.select_distinct_ranked_routes(
            [
                (alt_segs, "Live OpenStreetMap Bicycle Routing (OSRM)"),
                (alt_segs, "Live OpenStreetMap Street Routing (OSRM)"),
                (dir_only, "Live OpenStreetMap Bicycle Routing (OSRM)"),
            ],
            12.0,
            "08:30",
            "50%",
            12.0,
        )
        self.assertTrue(assert_equal(len(ranked), 2))
        self.assertTrue(
            assert_equal(sorted(ranked.keys()), ["Direct", "Safest"])
        )

        graph = routing.SafetyRoutingGraph()
        graph.add_node("a", origin)
        graph.add_node("b", destination)
        graph.add_edge("a", "b", segment)
        self.assertTrue(assert_equal(len(graph.nodes), 2))
        self.assertTrue(assert_equal(len(graph.edges["a"]), 1))
        self.assertTrue(
            assert_equal(graph.calculate_edge_cost(segment, "Direct") > 0, True)
        )
        path = graph.find_shortest_safety_path("a", "b", "Safest")
        self.assertTrue(assert_equal(len(path), 1))

        delaware_graph = routing.SafetyRoutingGraph()
        for node_id in (
            "start",
            "ud_green",
            "glasgow_park",
            "canal_west",
            "brookside",
            "wilson_rd",
            "porter_rd",
            "rt896_mid",
            "end",
        ):
            delaware_graph.add_node(node_id, origin)
        routing.add_delaware_safest_edges(delaware_graph)
        routing.add_delaware_balanced_edges(delaware_graph)
        routing.add_delaware_direct_edges(delaware_graph)
        self.assertTrue(assert_equal(len(delaware_graph.edges["start"]), 3))

        full_graph = routing.build_default_corridor_graph()
        self.assertTrue(assert_equal(len(full_graph.nodes), 9))

        warnings = routing.collect_route_warnings([segment], "08:00")
        self.assertTrue(assert_equal(len(warnings), 1))

        packaged = routing.package_route_option(
            "Safest", [segment], 12.0, "12:00", "Safe path", 15.0
        )
        self.assertTrue(assert_equal(packaged.route_type, "Safest"))

        curved_points = routing.interpolate_corridor_points(
            origin, destination, 0.01, steps=4
        )
        self.assertTrue(assert_equal(len(curved_points), 5))

        safe_segs = routing.build_generic_safest_segments(
            origin, destination, "Start", "End", 0.01, 5.0
        )
        bal_segs = routing.build_generic_balanced_segments(
            origin, destination, "Start", "End", 0.01, 5.0
        )
        dir_segs = routing.build_generic_direct_segments(
            origin, destination, "Start", "End", 5.0
        )
        self.assertTrue(assert_equal(len(safe_segs), 4))
        self.assertTrue(assert_equal(len(bal_segs), 3))
        self.assertTrue(assert_equal(len(dir_segs), 3))

        generic_routes = routing.build_generic_corridor_routes(
            Coordinate(40.7661, -73.9772),
            Coordinate(40.7126, -74.0048),
            "Central Park",
            "Brooklyn Bridge",
            12.0,
            "09:00",
        )
        self.assertTrue(assert_equal(len(generic_routes), 3))

        planned = routing.plan_bicycle_routes(
            origin, destination, "Newark, DE", "Kirkwood, DE", allow_remote=False
        )
        self.assertTrue(assert_equal(len(planned), 3))
        cached_planned = routing.plan_bicycle_routes_cached(
            39.6765,
            -75.7471,
            39.5718,
            -75.6961,
            "Newark, DE",
            "Kirkwood, DE",
            12.0,
            "08:30",
            "50%",
            False,
        )
        self.assertTrue(assert_equal(len(cached_planned), 3))
        recalibrated = routing.recalibrate_routes_for_speed(planned, 20.0)
        self.assertTrue(
            assert_equal(
                recalibrated["Safest"].estimated_duration_mins
                < planned["Safest"].estimated_duration_mins,
                True,
            )
        )

    def test_storage_and_visuals_helpers(self) -> None:
        """Verify every testable function in storage.py and visuals.py."""
        self.assertTrue(
            assert_equal(storage.xml_escape("A & B <C>"), "A &amp; B &lt;C&gt;")
        )

        origin = Coordinate(39.676456, -75.747050)
        destination = Coordinate(39.571807, -75.696079)
        routes = routing.plan_bicycle_routes(
            origin, destination, "Newark, DE", "Kirkwood, DE", allow_remote=False
        )
        gpx_xml = storage.export_route_to_gpx(
            routes["Safest"], "Newark, DE", "Kirkwood, DE"
        )
        self.assertTrue(assert_equal("<gpx" in gpx_xml, True))

        self.assertTrue(
            assert_equal(visuals.escape_svg_text("X < Y"), "X &lt; Y")
        )
        coords = visuals.collect_route_coordinates(routes)
        self.assertTrue(assert_equal(len(coords) > 0, True))

        self.assertTrue(
            assert_equal(visuals.get_route_short_label("Safest"), "Saf")
        )
        self.assertTrue(
            assert_equal(visuals.get_route_short_label("Balanced"), "Bal")
        )
        self.assertTrue(
            assert_equal(visuals.get_route_short_label("Direct"), "Dir")
        )
        flat_opt = visuals.flatten_option_points(routes["Safest"])
        self.assertTrue(assert_equal(len(flat_opt) >= 2, True))
        badge_pt = visuals.find_distinct_badge_point(
            routes["Safest"], routes, []
        )
        self.assertTrue(assert_equal(badge_pt is not None, True))

        map_poly_json = visuals.build_map_polylines_json(routes, "Safest")
        parsed_polys = json.loads(map_poly_json)
        badges = [item for item in parsed_polys if item.get("kind") == "badge"]
        active_lines = [
            item
            for item in parsed_polys
            if item.get("kind") == "line" and item.get("isActive")
        ]
        self.assertTrue(assert_equal(len(badges), 3))
        self.assertTrue(assert_equal(len(active_lines), 1))
        self.assertTrue(
            assert_equal(badges[0].get("shortText", "").startswith("Saf"), True)
        )
        self.assertTrue(
            assert_equal(
                badges[0].get("fullText", "").startswith("Safest"), True
            )
        )

        seg_poly_json = visuals.build_segment_polyline_json(
            routes["Safest"].segments[0]
        )
        parsed_seg_poly = json.loads(seg_poly_json)
        self.assertTrue(assert_equal(len(parsed_seg_poly), 1))

        projected = visuals.project_coordinate(
            origin, (39.5, 0.2, -75.8, 0.2), (50.0, 40.0, 500.0, 200.0)
        )
        self.assertTrue(assert_equal(len(projected), 2))
        grid_lines = visuals.build_svg_grid_lines(56, 42, 52, 640, 340, "#ccc")
        self.assertTrue(assert_equal(len(grid_lines), 8))
        legend_items = visuals.build_svg_legend(340, "#475569")
        self.assertTrue(assert_equal(len(legend_items), 10))
        corridor_svg = visuals.build_corridor_comparison_svg(routes, "Safest")
        self.assertTrue(assert_equal("<polyline" in corridor_svg, True))
        profile_svg = visuals.build_safety_profile_svg(routes["Safest"])
        self.assertTrue(
            assert_equal("Segment Safety Spectrum" in profile_svg, True)
        )

    def test_main_bakery_suite_passes_all_routes_and_helpers(self) -> None:
        """Run main.run_bakery_unit_tests() and assert zero bakery failures."""
        failures_before = student_tests.failures
        main.run_bakery_unit_tests()
        self.assertEqual(student_tests.failures, failures_before)


if __name__ == "__main__":
    unittest.main()
