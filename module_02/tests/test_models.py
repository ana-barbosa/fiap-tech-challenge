import unittest

from pydantic import ValidationError

from src.models import (
    DeliveryNode,
    Depot,
    Location,
    ProblemInput,
    Route,
    Solution,
    VehicleConfig,
)


def make_problem(**overrides) -> dict:
    """Helper to build a valid ProblemInput dict, with optional overrides."""
    base = {
        "depot": {"location": [0.0, 0.0]},
        "vehicles": {"count": 2, "capacity": 50.0, "max_range": 1000.0},
        "deliveries": [
            {"location": [1.0, 0.0], "priority": "regular", "demand": 10.0},
            {"location": [2.0, 0.0], "priority": "critical", "demand": 20.0},
        ],
    }
    base.update(overrides)
    return base


class TestLocation(unittest.TestCase):
    def test_distance_to_known_value(self):
        a = Location(location=(0.0, 0.0))
        b = Location(location=(3.0, 4.0))
        self.assertAlmostEqual(a.distance_to(b), 5.0)

    def test_distance_to_is_symmetric(self):
        a = Location(location=(1.0, 2.0))
        b = Location(location=(4.0, 6.0))
        self.assertAlmostEqual(a.distance_to(b), b.distance_to(a))

    def test_distance_to_same_location(self):
        a = Location(location=(3.0, 7.0))
        self.assertEqual(a.distance_to(a), 0.0)

    def test_distance_to_works_across_subclasses(self):
        depot = Depot(location=(0.0, 0.0))
        node = DeliveryNode(location=(3.0, 4.0), demand=5.0)
        self.assertAlmostEqual(depot.distance_to(node), 5.0)
        self.assertAlmostEqual(node.distance_to(depot), 5.0)

    def test_distance_to_negative_coordinates(self):
        a = Location(location=(-3.0, -4.0))
        b = Location(location=(0.0, 0.0))
        self.assertAlmostEqual(a.distance_to(b), 5.0)


class TestDeliveryNode(unittest.TestCase):
    def test_valid_node(self):
        node = DeliveryNode(location=(1.0, 2.0), priority="critical", demand=10.0)
        self.assertEqual(node.priority, "critical")
        self.assertEqual(node.demand, 10.0)

    def test_default_priority_is_regular(self):
        node = DeliveryNode(location=(1.0, 2.0), demand=5.0)
        self.assertEqual(node.priority, "regular")

    def test_demand_must_be_positive(self):
        with self.assertRaises(ValidationError):
            DeliveryNode(location=(1.0, 2.0), demand=0.0)

    def test_demand_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            DeliveryNode(location=(1.0, 2.0), demand=-5.0)

    def test_priority_rejects_invalid_value(self):
        with self.assertRaises(ValidationError):
            DeliveryNode(location=(1.0, 2.0), demand=5.0, priority="urgent")


class TestVehicleConfig(unittest.TestCase):
    def test_valid_config(self):
        config = VehicleConfig(count=3, capacity=100.0, max_range=500.0)
        self.assertEqual(config.count, 3)

    def test_count_must_be_positive(self):
        with self.assertRaises(ValidationError):
            VehicleConfig(count=0, capacity=100.0, max_range=500.0)

    def test_capacity_must_be_positive(self):
        with self.assertRaises(ValidationError):
            VehicleConfig(count=1, capacity=0.0, max_range=500.0)

    def test_max_range_must_be_positive(self):
        with self.assertRaises(ValidationError):
            VehicleConfig(count=1, capacity=100.0, max_range=0.0)


class TestProblemInputValidators(unittest.TestCase):
    def test_valid_problem_loads(self):
        problem = ProblemInput.model_validate(make_problem())
        self.assertEqual(len(problem.deliveries), 2)

    def test_total_demand_exceeds_fleet_capacity(self):
        data = make_problem(
            vehicles={"count": 1, "capacity": 10.0, "max_range": 1000.0}
        )
        with self.assertRaises(ValidationError) as ctx:
            ProblemInput.model_validate(data)
        self.assertIn("Total delivery demand", str(ctx.exception))

    def test_single_node_exceeds_vehicle_capacity(self):
        data = make_problem(
            vehicles={"count": 2, "capacity": 15.0, "max_range": 1000.0},
            deliveries=[
                {"location": [1.0, 0.0], "priority": "regular", "demand": 10.0},
                {"location": [2.0, 0.0], "priority": "regular", "demand": 20.0},
            ],
        )
        with self.assertRaises(ValidationError) as ctx:
            ProblemInput.model_validate(data)
        self.assertIn("exceeds vehicle capacity", str(ctx.exception))

    def test_node_unreachable_due_to_range(self):
        data = make_problem(
            vehicles={"count": 2, "capacity": 50.0, "max_range": 1.0},
            deliveries=[
                {"location": [1.0, 0.0], "priority": "regular", "demand": 10.0},
            ],
        )
        with self.assertRaises(ValidationError) as ctx:
            ProblemInput.model_validate(data)
        self.assertIn("unreachable", str(ctx.exception))

    def test_exactly_at_capacity_is_valid(self):
        data = make_problem(
            vehicles={"count": 1, "capacity": 30.0, "max_range": 1000.0},
            deliveries=[
                {"location": [1.0, 0.0], "priority": "regular", "demand": 10.0},
                {"location": [2.0, 0.0], "priority": "regular", "demand": 20.0},
            ],
        )
        problem = ProblemInput.model_validate(data)
        self.assertEqual(len(problem.deliveries), 2)

    def test_exactly_at_range_is_valid(self):
        # round trip to (0.5, 0.0) from (0.0, 0.0) = 1.0
        data = make_problem(
            vehicles={"count": 1, "capacity": 50.0, "max_range": 1.0},
            deliveries=[
                {"location": [0.5, 0.0], "priority": "regular", "demand": 10.0},
            ],
        )
        problem = ProblemInput.model_validate(data)
        self.assertEqual(len(problem.deliveries), 1)

    def test_empty_deliveries_rejected(self):
        data = make_problem(deliveries=[])
        with self.assertRaises(ValidationError):
            ProblemInput.model_validate(data)


class TestRoute(unittest.TestCase):
    def _make_route(self, nodes, depot=None) -> Route:
        if depot is None:
            depot = Depot(location=(0.0, 0.0))
        return Route(vehicle_index=0, depot=depot, nodes=nodes)

    def test_total_distance_km_empty_nodes(self):
        route = self._make_route([])
        self.assertEqual(route.total_distance_km, 0.0)

    def test_total_distance_km_single_node(self):
        # depot(0,0) → node(3,4) → depot = 5 + 5 = 10 degrees * 111 = 1110.0 km
        node = DeliveryNode(location=(3.0, 4.0), demand=10.0)
        route = self._make_route([node])
        self.assertAlmostEqual(route.total_distance_km, 1110.0)

    def test_total_demand(self):
        nodes = [
            DeliveryNode(location=(1.0, 0.0), demand=10.0),
            DeliveryNode(location=(2.0, 0.0), demand=20.0),
        ]
        route = self._make_route(nodes)
        self.assertAlmostEqual(route.total_demand, 30.0)

    def test_critical_and_regular_stops(self):
        nodes = [
            DeliveryNode(location=(1.0, 0.0), demand=10.0, priority="critical"),
            DeliveryNode(location=(2.0, 0.0), demand=10.0, priority="critical"),
            DeliveryNode(location=(3.0, 0.0), demand=10.0, priority="regular"),
        ]
        route = self._make_route(nodes)
        self.assertEqual(route.critical_stops, 2)
        self.assertEqual(route.regular_stops, 1)

    def test_depot_excluded_from_serialisation(self):
        node = DeliveryNode(location=(1.0, 0.0), demand=10.0)
        route = self._make_route([node])
        dumped = route.model_dump()
        self.assertNotIn("depot", dumped)


class TestSolution(unittest.TestCase):
    def _make_solution(self) -> Solution:
        depot = Depot(location=(0.0, 0.0))
        vehicles = VehicleConfig(count=2, capacity=50.0, max_range=1000.0)
        routes = [
            Route(
                vehicle_index=0,
                depot=depot,
                nodes=[DeliveryNode(location=(1.0, 0.0), demand=10.0)],
            ),
            Route(
                vehicle_index=1,
                depot=depot,
                nodes=[DeliveryNode(location=(2.0, 0.0), demand=20.0)],
            ),
        ]
        return Solution(
            best_fitness=42.0,
            stopping_reason="test",
            depot=depot,
            vehicles=vehicles,
            routes=routes,
        )

    def test_total_vehicles_used(self):
        self.assertEqual(self._make_solution().total_vehicles_used, 2)

    def test_total_demand_served(self):
        self.assertAlmostEqual(self._make_solution().total_demand_served, 30.0)

    def test_depot_present_in_serialisation(self):
        dumped = self._make_solution().model_dump()
        self.assertIn("depot", dumped)
        self.assertEqual(dumped["depot"]["location"], (0.0, 0.0))
