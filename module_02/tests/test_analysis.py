import unittest

from src.analysis import _format_route, _solution_summary


def make_route(
    vehicle_index: int = 0,
    total_demand: float = 30.0,
    total_distance_km: float = 500.0,
    critical_stops: int = 1,
    regular_stops: int = 2,
    nodes: list | None = None,
) -> dict:
    if nodes is None:
        nodes = [
            {
                "location": [48.8566, 2.3522],
                "priority": "critical",
                "demand": 10.0,
                "stop_number": 1,
            },
            {
                "location": [51.5074, -0.1278],
                "priority": "regular",
                "demand": 20.0,
                "stop_number": 2,
            },
        ]
    return {
        "vehicle_index": vehicle_index,
        "total_demand": total_demand,
        "total_distance_km": total_distance_km,
        "critical_stops": critical_stops,
        "regular_stops": regular_stops,
        "nodes": nodes,
    }


def make_solution(
    routes: list | None = None,
    depot_location: list | None = None,
    total_vehicles_used: int = 2,
    total_vehicles_available: int = 5,
    total_demand_served: float = 60.0,
    best_fitness: float = 123.456789,
    stopping_reason: str = "Converged after 500 generations without improvement",
    vehicle_capacity: float = 100.0,
    vehicle_max_range: float = 8.7,
) -> dict:
    if depot_location is None:
        depot_location = [40.4168, -3.7038]
    if routes is None:
        routes = [make_route(vehicle_index=0), make_route(vehicle_index=1)]
    return {
        "depot": {"location": depot_location},
        "routes": routes,
        "total_vehicles_used": total_vehicles_used,
        "total_vehicles_available": total_vehicles_available,
        "total_demand_served": total_demand_served,
        "best_fitness": best_fitness,
        "stopping_reason": stopping_reason,
        "vehicles": {"capacity": vehicle_capacity, "max_range": vehicle_max_range},
    }


class TestFormatRoute(unittest.TestCase):
    def test_header_uses_one_based_index(self):
        result = _format_route(make_route(vehicle_index=0), index=0)
        self.assertIn("Route 1", result)

    def test_header_shows_vehicle_index(self):
        result = _format_route(make_route(vehicle_index=3), index=0)
        self.assertIn("Vehicle 3", result)

    def test_index_offset_applied(self):
        result = _format_route(make_route(), index=2)
        self.assertIn("Route 3", result)

    def test_total_demand_present(self):
        result = _format_route(make_route(total_demand=77.5), index=0)
        self.assertIn("77.5", result)

    def test_total_distance_present(self):
        result = _format_route(make_route(total_distance_km=1234.56), index=0)
        self.assertIn("1234.56 km", result)

    def test_critical_stop_count_present(self):
        result = _format_route(make_route(critical_stops=3), index=0)
        self.assertIn("3", result)

    def test_regular_stop_count_present(self):
        result = _format_route(make_route(regular_stops=5), index=0)
        self.assertIn("5", result)

    def test_critical_node_tagged_correctly(self):
        route = make_route(
            nodes=[
                {
                    "location": [1.0, 2.0],
                    "priority": "critical",
                    "demand": 10.0,
                    "stop_number": 1,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("‼ CRITICAL", result)

    def test_regular_node_tagged_correctly(self):
        route = make_route(
            nodes=[
                {
                    "location": [1.0, 2.0],
                    "priority": "regular",
                    "demand": 10.0,
                    "stop_number": 1,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("regular", result)
        self.assertNotIn("CRITICAL", result)

    def test_stop_number_present(self):
        route = make_route(
            nodes=[
                {
                    "location": [1.0, 2.0],
                    "priority": "regular",
                    "demand": 5.0,
                    "stop_number": 3,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("Stop  3", result)

    def test_node_coordinates_present(self):
        route = make_route(
            nodes=[
                {
                    "location": [48.8566, 2.3522],
                    "priority": "regular",
                    "demand": 5.0,
                    "stop_number": 1,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("48.8566", result)
        self.assertIn("2.3522", result)

    def test_node_demand_present(self):
        route = make_route(
            nodes=[
                {
                    "location": [1.0, 2.0],
                    "priority": "regular",
                    "demand": 19.3,
                    "stop_number": 1,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("demand=19.3", result)

    def test_empty_nodes_returns_header_only(self):
        route = make_route(nodes=[])
        result = _format_route(route, index=0)
        self.assertIn("Route 1", result)
        self.assertNotIn("Stop  1", result)

    def test_multiple_nodes_all_present(self):
        route = make_route(
            nodes=[
                {
                    "location": [1.0, 0.0],
                    "priority": "regular",
                    "demand": 5.0,
                    "stop_number": 1,
                },
                {
                    "location": [2.0, 0.0],
                    "priority": "critical",
                    "demand": 8.0,
                    "stop_number": 2,
                },
                {
                    "location": [3.0, 0.0],
                    "priority": "regular",
                    "demand": 3.0,
                    "stop_number": 3,
                },
            ]
        )
        result = _format_route(route, index=0)
        self.assertIn("Stop  1", result)
        self.assertIn("Stop  2", result)
        self.assertIn("Stop  3", result)


class TestSolutionSummary(unittest.TestCase):
    def test_depot_coordinates_present(self):
        result = _solution_summary(make_solution(depot_location=[40.4168, -3.7038]))
        self.assertIn("40.4168", result)
        self.assertIn("-3.7038", result)

    def test_total_vehicles_used_present(self):
        result = _solution_summary(
            make_solution(total_vehicles_used=4, total_vehicles_available=6)
        )
        self.assertIn("4 / 6", result)

    def test_vehicles_available_present(self):
        result = _solution_summary(
            make_solution(total_vehicles_used=2, total_vehicles_available=8)
        )
        self.assertIn("2 / 8", result)

    def test_vehicle_capacity_present(self):
        result = _solution_summary(make_solution(vehicle_capacity=75.0))
        self.assertIn("75.0", result)

    def test_vehicle_max_range_present(self):
        result = _solution_summary(make_solution(vehicle_max_range=12.5))
        self.assertIn("12.5", result)

    def test_total_demand_served_present(self):
        result = _solution_summary(make_solution(total_demand_served=399.1))
        self.assertIn("399.1", result)

    def test_route_count_present(self):
        routes = [make_route(vehicle_index=i) for i in range(3)]
        result = _solution_summary(make_solution(routes=routes))
        self.assertIn("Routes           : 3", result)

    def test_fitness_formatted_to_four_decimal_places(self):
        result = _solution_summary(make_solution(best_fitness=123.456789))
        self.assertIn("123.4568", result)

    def test_stopping_reason_present(self):
        result = _solution_summary(
            make_solution(stopping_reason="Reached time limit of 600s")
        )
        self.assertIn("Reached time limit of 600s", result)

    def test_route_details_section_present(self):
        result = _solution_summary(make_solution())
        self.assertIn("Route details:", result)

    def test_each_route_block_included(self):
        routes = [make_route(vehicle_index=0), make_route(vehicle_index=1)]
        result = _solution_summary(make_solution(routes=routes))
        self.assertIn("Route 1", result)
        self.assertIn("Route 2", result)

    def test_empty_routes_list_does_not_crash(self):
        result = _solution_summary(make_solution(routes=[], total_vehicles_used=0))
        self.assertIn("Routes           : 0", result)

    def test_negative_depot_coordinates_handled(self):
        result = _solution_summary(make_solution(depot_location=[-15.7801, -47.9292]))
        self.assertIn("-15.7801", result)
        self.assertIn("-47.9292", result)
