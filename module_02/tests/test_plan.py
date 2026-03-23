import tempfile
import unittest
from pathlib import Path
from typing import Any, Literal

import tomllib

from src.models import DeliveryNode, Depot, ProblemInput, VehicleConfig
from src.plan import _save_solution
from src.stopping import StoppingCondition


def make_depot(lat: float = 0.0, lon: float = 0.0) -> Depot:
    return Depot(location=(lat, lon))


def make_node(
    lat: float,
    lon: float,
    demand: float = 10.0,
    priority: Literal["critical", "regular"] = "regular",
) -> DeliveryNode:
    return DeliveryNode(location=(lat, lon), demand=demand, priority=priority)


def make_problem(
    depot: Depot | None = None,
    nodes: list[DeliveryNode] | None = None,
    count: int = 8,
    capacity: float = 100.0,
    max_range: float = 999.0,
) -> ProblemInput:
    if depot is None:
        depot = make_depot()
    if nodes is None:
        nodes = [make_node(1.0, 0.0)]
    return ProblemInput(
        depot=depot,
        vehicles=VehicleConfig(count=count, capacity=capacity, max_range=max_range),
        deliveries=nodes,
    )


def make_stopping(**overrides: Any) -> StoppingCondition:
    base: dict[str, Any] = {
        "max_seconds": 60,
        "patience": 10,
        "threshold": 0.0,
        "generations": 1,
    }
    base.update(overrides)
    sc = StoppingCondition(**base)
    sc.update(100.0)  # advance one generation so reason is populated
    return sc


class TestSaveSolutionOutputPath(unittest.TestCase):
    def test_output_file_named_after_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            input_path = Path("examples/att48.toml")
            sub_routes = [[make_node(1.0, 0.0)]]
            sc = make_stopping()

            _save_solution(
                input_path,
                make_problem(nodes=sub_routes[0]),
                sub_routes,
                42.0,
                sc,
                output_dir,
            )

            self.assertTrue((output_dir / "att48.toml").exists())

    def test_input_directory_is_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            input_path = Path("some/deeply/nested/brazil27.toml")
            sub_routes = [[make_node(1.0, 0.0)]]
            sc = make_stopping()

            _save_solution(
                input_path,
                make_problem(nodes=sub_routes[0]),
                sub_routes,
                42.0,
                sc,
                output_dir,
            )

            self.assertTrue((output_dir / "brazil27.toml").exists())
            self.assertFalse((output_dir / "some/deeply/nested/brazil27.toml").exists())

    def test_creates_output_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "does" / "not" / "exist"
            self.assertFalse(output_dir.exists())

            _save_solution(
                Path("att48.toml"),
                make_problem(nodes=[[make_node(1.0, 0.0)]][0]),
                [[make_node(1.0, 0.0)]],
                42.0,
                make_stopping(),
                output_dir,
            )

            self.assertTrue(output_dir.exists())


class TestSaveSolutionRootKeys(unittest.TestCase):
    def _load(self, tmp: str, filename: str = "att48.toml") -> dict:
        with open(Path(tmp) / filename, "rb") as f:
            return tomllib.load(f)

    def test_best_fitness_written_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                make_problem(),
                [[make_node(1.0, 0.0)]],
                123.45,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertAlmostEqual(data["best_fitness"], 123.45)

    def test_stopping_reason_written_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                make_problem(),
                [[make_node(1.0, 0.0)]],
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertIn("stopping_reason", data)
            self.assertIsInstance(data["stopping_reason"], str)
            self.assertTrue(len(data["stopping_reason"]) > 0)

    def test_routes_key_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                make_problem(),
                [[make_node(1.0, 0.0)]],
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertIn("routes", data)

    def test_depot_location_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                make_problem(depot=make_depot(1.0, 2.0), nodes=[make_node(3.0, 4.0)]),
                [[make_node(3.0, 4.0)]],
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertIn("depot", data)
            self.assertEqual(data["depot"]["location"], [1.0, 2.0])

    def test_total_vehicles_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub_routes = [[make_node(1.0, 0.0)], [make_node(2.0, 0.0)]]
            _save_solution(
                Path("att48.toml"),
                make_problem(nodes=[make_node(1.0, 0.0), make_node(2.0, 0.0)]),
                sub_routes,
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertEqual(data["total_vehicles_used"], 2)

    def test_total_demand_served(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub_routes = [
                [make_node(1.0, 0.0, demand=10.0), make_node(2.0, 0.0, demand=20.0)]
            ]
            _save_solution(
                Path("att48.toml"),
                make_problem(nodes=sub_routes[0]),
                sub_routes,
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertAlmostEqual(data["total_demand_served"], 30.0)

    def test_vehicles_written_to_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                make_problem(count=4, capacity=50.0, max_range=200.0),
                [[make_node(1.0, 0.0)]],
                0.0,
                make_stopping(),
                Path(tmp),
            )
            data = self._load(tmp)
            self.assertIn("vehicles", data)
            self.assertAlmostEqual(data["vehicles"]["capacity"], 50.0)
            self.assertAlmostEqual(data["vehicles"]["max_range"], 200.0)


class TestSaveSolutionRouteStructure(unittest.TestCase):
    def _save_and_load(
        self,
        sub_routes,
        depot: Depot = make_depot(),
        fitness: float = 0.0,
    ) -> dict:
        all_nodes = [node for sub in sub_routes for node in sub]
        problem = make_problem(depot=depot, nodes=all_nodes, count=len(sub_routes))
        with tempfile.TemporaryDirectory() as tmp:
            _save_solution(
                Path("att48.toml"),
                problem,
                sub_routes,
                fitness,
                make_stopping(),
                Path(tmp),
            )
            with open(Path(tmp) / "att48.toml", "rb") as f:
                return tomllib.load(f)

    def test_vehicle_index_increments(self):
        sub_routes = [
            [make_node(1.0, 0.0)],
            [make_node(2.0, 0.0)],
            [make_node(3.0, 0.0)],
        ]
        data = self._save_and_load(sub_routes)
        indices = [r["vehicle_index"] for r in data["routes"]]
        self.assertEqual(indices, [0, 1, 2])

    def test_correct_number_of_routes(self):
        sub_routes = [[make_node(1.0, 0.0)], [make_node(2.0, 0.0)]]
        data = self._save_and_load(sub_routes)
        self.assertEqual(len(data["routes"]), 2)

    def test_node_location_serialised_as_list(self):
        # tuples are not valid TOML — must be written and read back as lists
        sub_routes = [[make_node(3.0, 4.0)]]
        data = self._save_and_load(sub_routes)
        location = data["routes"][0]["nodes"][0]["location"]
        self.assertIsInstance(location, list)
        self.assertEqual(location, [3.0, 4.0])

    def test_node_priority_and_demand_correct(self):
        sub_routes = [[make_node(1.0, 0.0, demand=17.8, priority="critical")]]
        data = self._save_and_load(sub_routes)
        node = data["routes"][0]["nodes"][0]
        self.assertEqual(node["priority"], "critical")
        self.assertAlmostEqual(node["demand"], 17.8)

    def test_multi_vehicle_multi_node(self):
        sub_routes = [
            [make_node(1.0, 0.0, demand=5.0), make_node(2.0, 0.0, demand=8.0)],
            [make_node(3.0, 0.0, demand=12.0), make_node(4.0, 0.0, demand=3.0)],
        ]
        data = self._save_and_load(sub_routes)

        self.assertEqual(len(data["routes"]), 2)
        self.assertEqual(len(data["routes"][0]["nodes"]), 2)
        self.assertEqual(len(data["routes"][1]["nodes"]), 2)
        self.assertEqual(data["routes"][0]["vehicle_index"], 0)
        self.assertEqual(data["routes"][1]["vehicle_index"], 1)
        self.assertAlmostEqual(data["routes"][0]["nodes"][0]["demand"], 5.0)
        self.assertAlmostEqual(data["routes"][1]["nodes"][1]["demand"], 3.0)

    def test_total_distance_km_is_positive(self):
        sub_routes = [[make_node(3.0, 4.0), make_node(6.0, 8.0)]]
        data = self._save_and_load(sub_routes)
        self.assertGreater(data["routes"][0]["total_distance_km"], 0.0)

    def test_total_demand_per_route(self):
        sub_routes = [
            [make_node(1.0, 0.0, demand=10.0), make_node(2.0, 0.0, demand=15.0)]
        ]
        data = self._save_and_load(sub_routes)
        self.assertAlmostEqual(data["routes"][0]["total_demand"], 25.0)

    def test_critical_and_regular_stop_counts(self):
        sub_routes = [
            [
                make_node(1.0, 0.0, priority="critical"),
                make_node(2.0, 0.0, priority="critical"),
                make_node(3.0, 0.0, priority="regular"),
            ]
        ]
        data = self._save_and_load(sub_routes)
        self.assertEqual(data["routes"][0]["critical_stops"], 2)
        self.assertEqual(data["routes"][0]["regular_stops"], 1)

    def test_stop_number_is_one_indexed(self):
        sub_routes = [[make_node(1.0, 0.0), make_node(2.0, 0.0), make_node(3.0, 0.0)]]
        data = self._save_and_load(sub_routes)
        stop_numbers = [n["stop_number"] for n in data["routes"][0]["nodes"]]
        self.assertEqual(stop_numbers, [1, 2, 3])

    def test_depot_excluded_from_route_nodes(self):
        # depot should appear at root level only, not inside each route
        sub_routes = [[make_node(1.0, 0.0)]]
        data = self._save_and_load(sub_routes)
        self.assertNotIn("depot", data["routes"][0])
