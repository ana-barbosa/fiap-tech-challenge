import unittest
from typing import Any, Literal

from src.genetic_algorithm import (
    calculate_fitness,
    generate_random_population,
    mutate,
    order_crossover,
    sort_population,
    split_route_into_vehicles,
)
from src.models import DeliveryNode, Depot, VehicleConfig


def make_depot(lat: float = 0.0, lon: float = 0.0) -> Depot:
    return Depot(location=(lat, lon))


def make_node(
    lat: float,
    lon: float,
    demand: float = 10.0,
    priority: Literal["critical", "regular"] = "regular",
) -> DeliveryNode:
    return DeliveryNode(location=(lat, lon), demand=demand, priority=priority)


def make_vehicles(**overrides: Any) -> VehicleConfig:
    base: dict[str, Any] = {"count": 4, "capacity": 100.0, "max_range": 1000.0}
    base.update(overrides)
    return VehicleConfig(**base)


class TestGenerateRandomPopulation(unittest.TestCase):
    def setUp(self) -> None:
        self.depot = make_depot()
        self.deliveries = [make_node(float(i), 0.0) for i in range(1, 6)]

    def test_returns_correct_population_size(self):
        population = generate_random_population(self.depot, self.deliveries, 10)
        self.assertEqual(len(population), 10)

    def test_each_route_contains_all_nodes(self):
        population = generate_random_population(self.depot, self.deliveries, 10)
        expected = {n.location for n in self.deliveries}
        for route in population:
            self.assertEqual({n.location for n in route}, expected)

    def test_no_duplicates_within_route(self):
        population = generate_random_population(self.depot, self.deliveries, 10)
        for route in population:
            locations = [n.location for n in route]
            self.assertEqual(len(locations), len(set(locations)))

    def test_first_individual_is_nearest_neighbour(self):
        # NN from (0,0) should visit nodes in order 1,2,3,4,5 (closest first)
        population = generate_random_population(self.depot, self.deliveries, 10)
        nn_route = population[0]
        self.assertEqual(nn_route, self.deliveries)


class TestSplitRouteIntoVehicles(unittest.TestCase):
    def setUp(self) -> None:
        self.depot = make_depot()

    def test_all_nodes_appear_exactly_once(self):
        nodes = [make_node(float(i), 0.0) for i in range(1, 6)]
        vehicles = make_vehicles()
        sub_routes = split_route_into_vehicles(self.depot, nodes, vehicles)
        all_nodes = [n for sub in sub_routes for n in sub]
        self.assertEqual(
            sorted(all_nodes, key=lambda n: n.location),
            sorted(nodes, key=lambda n: n.location),
        )

    def test_single_vehicle_when_capacity_allows(self):
        nodes = [make_node(float(i), 0.0, demand=10.0) for i in range(1, 4)]
        vehicles = make_vehicles(count=4, capacity=100.0)
        sub_routes = split_route_into_vehicles(self.depot, nodes, vehicles)
        self.assertEqual(len(sub_routes), 1)

    def test_splits_when_capacity_exceeded(self):
        # Each node has demand 60, capacity is 100 → max 1 node per vehicle
        nodes = [make_node(float(i), 0.0, demand=60.0) for i in range(1, 4)]
        vehicles = make_vehicles(count=4, capacity=100.0)
        sub_routes = split_route_into_vehicles(self.depot, nodes, vehicles)
        self.assertGreater(len(sub_routes), 1)
        for sub in sub_routes:
            total = sum(n.demand for n in sub)
            self.assertLessEqual(total, 100.0)

    def test_splits_when_range_exceeded(self):
        # Nodes far from depot, small range forces splits
        nodes = [make_node(float(i) * 10, 0.0, demand=1.0) for i in range(1, 4)]
        vehicles = make_vehicles(count=4, capacity=100.0, max_range=25.0)
        sub_routes = split_route_into_vehicles(self.depot, nodes, vehicles)
        self.assertGreater(len(sub_routes), 1)

    def test_respects_vehicle_count_limit(self):
        nodes = [make_node(float(i), 0.0, demand=60.0) for i in range(1, 5)]
        vehicles = make_vehicles(count=2, capacity=100.0)
        sub_routes = split_route_into_vehicles(self.depot, nodes, vehicles)
        self.assertLessEqual(len(sub_routes), 2)

    def test_empty_route_returns_empty(self):
        vehicles = make_vehicles()
        sub_routes = split_route_into_vehicles(self.depot, [], vehicles)
        self.assertEqual(sub_routes, [])


class TestCalculateFitness(unittest.TestCase):
    def setUp(self) -> None:
        self.depot = make_depot(0.0, 0.0)
        self.vehicles = make_vehicles()

    def test_empty_route_returns_zero(self):
        self.assertEqual(calculate_fitness(self.depot, [], self.vehicles), 0.0)

    def test_single_node_distance(self):
        # depot(0,0) → node(3,4) → depot(0,0) = 5 + 5 = 10
        node = make_node(3.0, 4.0, demand=10.0)
        fitness = calculate_fitness(self.depot, [node], self.vehicles)
        self.assertAlmostEqual(fitness, 10.0)

    def test_critical_node_weighted_higher(self):
        node_regular = make_node(3.0, 4.0, demand=10.0, priority="regular")
        node_critical = make_node(3.0, 4.0, demand=10.0, priority="critical")
        fitness_regular = calculate_fitness(self.depot, [node_regular], self.vehicles)
        fitness_critical = calculate_fitness(self.depot, [node_critical], self.vehicles)
        self.assertGreater(fitness_critical, fitness_regular)

    def test_fitness_increases_with_distance(self):
        near = make_node(1.0, 0.0, demand=10.0)
        far = make_node(10.0, 0.0, demand=10.0)
        fitness_near = calculate_fitness(self.depot, [near], self.vehicles)
        fitness_far = calculate_fitness(self.depot, [far], self.vehicles)
        self.assertGreater(fitness_far, fitness_near)

    def test_weighted_distance_multi_node_route(self):
        # triggers the node → node loop in _weighted_route_distance
        nodes = [make_node(1.0, 0.0), make_node(2.0, 0.0), make_node(3.0, 0.0)]
        fitness = calculate_fitness(self.depot, nodes, self.vehicles)
        self.assertGreater(fitness, 0.0)


class TestOrderCrossover(unittest.TestCase):
    def setUp(self) -> None:
        self.nodes = [make_node(float(i), 0.0) for i in range(1, 6)]

    def test_child_contains_all_nodes_exactly_once(self):
        parent1 = self.nodes[:]
        parent2 = list(reversed(self.nodes))
        child = order_crossover(parent1, parent2)
        self.assertEqual(len(child), len(self.nodes))
        self.assertEqual({n.location for n in child}, {n.location for n in self.nodes})

    def test_child_has_no_duplicates(self):
        parent1 = self.nodes[:]
        parent2 = list(reversed(self.nodes))
        child = order_crossover(parent1, parent2)
        locations = [n.location for n in child]
        self.assertEqual(len(locations), len(set(locations)))

    def test_child_length_matches_parents(self):
        parent1 = self.nodes[:]
        parent2 = list(reversed(self.nodes))
        child = order_crossover(parent1, parent2)
        self.assertEqual(len(child), len(parent1))


class TestMutate(unittest.TestCase):
    def setUp(self) -> None:
        self.route = [make_node(float(i), 0.0) for i in range(1, 6)]

    def test_mutated_route_has_same_length(self):
        result = mutate(self.route, mutation_probability=1.0)
        self.assertEqual(len(result), len(self.route))

    def test_mutated_route_contains_same_nodes(self):
        result = mutate(self.route, mutation_probability=1.0)
        original_locations = {n.location for n in self.route}
        result_locations = {n.location for n in result}
        self.assertEqual(original_locations, result_locations)

    def test_no_mutation_when_probability_zero(self):
        result = mutate(self.route, mutation_probability=0.0)
        self.assertEqual(result, self.route)

    def test_single_node_route_not_mutated(self):
        single = [make_node(1.0, 0.0)]
        result = mutate(single, mutation_probability=1.0)
        self.assertEqual(result[0].location, single[0].location)

    def test_always_mutates_when_probability_one(self):
        # With a large enough route, inversion always changes the order
        route = [make_node(float(i), 0.0) for i in range(1, 20)]
        result = mutate(route, mutation_probability=1.0, mutation_intensity=1.0)
        self.assertNotEqual(result, route)


class TestSortPopulation(unittest.TestCase):
    def setUp(self) -> None:
        self.nodes = [make_node(float(i), 0.0) for i in range(1, 4)]

    def test_sorted_ascending_by_fitness(self):
        population = [self.nodes[:], self.nodes[:], self.nodes[:]]
        fitness = [30.0, 10.0, 20.0]
        sorted_pop, sorted_fit = sort_population(population, fitness)
        self.assertEqual(list(sorted_fit), [10.0, 20.0, 30.0])

    def test_population_order_matches_fitness(self):
        route_a = [make_node(1.0, 0.0)]
        route_b = [make_node(2.0, 0.0)]
        route_c = [make_node(3.0, 0.0)]
        population = [route_a, route_b, route_c]
        fitness = [30.0, 10.0, 20.0]
        sorted_pop, sorted_fit = sort_population(population, fitness)
        self.assertEqual(sorted_pop[0], route_b)
        self.assertEqual(sorted_pop[1], route_c)
        self.assertEqual(sorted_pop[2], route_a)
