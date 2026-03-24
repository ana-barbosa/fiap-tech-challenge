import copy
import random
from typing import List, Tuple

from .constants import CRITICAL_PRIORITY_WEIGHT
from .models import DeliveryNode, Depot, Location, VehicleConfig


def _nearest_neighbour_route(
    depot: Depot, deliveries: List[DeliveryNode]
) -> List[DeliveryNode]:
    unvisited = deliveries[:]
    route = []
    # Starting from the depot, always move to the closest unvisited node.
    current: Location = depot

    while unvisited:
        nearest = min(unvisited, key=lambda node: current.distance_to(node))
        route.append(nearest)
        current = nearest
        unvisited.remove(nearest)

    return route


def generate_random_population(
    depot: Depot, deliveries: List[DeliveryNode], population_size: int
) -> List[List[DeliveryNode]]:
    """
    Generate a random population of routes for a given set of delivery nodes.

    Parameters:
    - depot (Depot): The starting and ending point of each route.
    - deliveries (List[DeliveryNode]): The list of delivery nodes to visit.
    - population_size (int): The number of routes to generate.

    Returns:
    List[List[DeliveryNode]]: A list of flat routes, each being a list of all delivery
                              nodes.
    """
    # Seed with one NN solution for a strong starting point
    population = [_nearest_neighbour_route(depot, deliveries)]

    # Fill the rest with random permutations for diversity
    while len(population) < population_size:
        population.append(random.sample(deliveries, len(deliveries)))

    return population


def split_route_into_vehicles(
    depot: Depot, route: List[DeliveryNode], vehicles: VehicleConfig
) -> List[List[DeliveryNode]]:
    """
    Greedily cuts the flat route into sub-routes whenever adding the next
    node would exceed the vehicle's capacity or range. Each sub-route
    implicitly starts and ends at the depot.

    Parameters:
    - depot (Depot): The starting and ending point of every sub-route.
    - route (List[DeliveryNode]): Flat ordered list of all delivery nodes.
    - vehicles (VehicleConfig): Fleet configuration holding capacity, max_range and
                                count.

    Returns:
    List[List[DeliveryNode]]: One sub-route per vehicle used.
    """
    sub_routes: List[List[DeliveryNode]] = []
    current_sub_route: List[DeliveryNode] = []
    current_demand = 0.0
    current_distance = 0.0
    current: Location = depot  # always start from depot

    for node in route:
        # Distance to the next delivery node
        leg = current.distance_to(node)
        # Distance to go back to depot.
        # The vehicle must always be able to come back within its range.
        return_leg = node.distance_to(depot)

        demand_ok = (current_demand + node.demand) <= vehicles.capacity
        range_ok = (current_distance + leg + return_leg) <= vehicles.max_range
        can_open_new_vehicle = len(sub_routes) < vehicles.count - 1

        if (
            current_sub_route
            and (not demand_ok or not range_ok)
            and can_open_new_vehicle
        ):
            # Close this sub-route, open a new one from depot
            sub_routes.append(current_sub_route)
            current_sub_route = []
            current_demand = 0.0
            current_distance = 0.0
            current = depot  # reset to depot

        current_sub_route.append(node)
        current_demand += node.demand
        current_distance += current.distance_to(node)
        current = node

    # Make sure to always add the last sub route to the list
    if current_sub_route:
        sub_routes.append(current_sub_route)

    return sub_routes


def _weighted_route_distance(depot: Depot, route: List[DeliveryNode]) -> float:
    if not route:
        return 0.0

    def leg_weight(node: DeliveryNode) -> float:
        # By multiplying critical legs by CRITICAL_PRIORITY_WEIGHT, we're telling
        # the GA that traveling to a critical node is "twice as expensive". So
        # the GA will naturally evolve routes that:
        # 1 - Place critical nodes closer to the depot in the route order
        # 2 - Group critical nodes together to avoid long legs between them
        # But note that it doesn't strictly enforce visit order.
        return CRITICAL_PRIORITY_WEIGHT if node.priority == "critical" else 1.0

    # depot → first node
    distance = depot.distance_to(route[0]) * leg_weight(route[0])

    # node → node
    for i in range(len(route) - 1):
        distance += route[i].distance_to(route[i + 1]) * leg_weight(route[i + 1])

    # last node → depot (no weight on return leg)
    distance += route[-1].distance_to(depot)

    return distance


def calculate_fitness(
    depot: Depot, route: List[DeliveryNode], vehicles: VehicleConfig
) -> float:
    """
    Calculate the fitness (total weighted travel distance) of a VRP solution.

    The flat route is first split into sub-routes via split_route_into_vehicles(),
    respecting vehicle capacity and range constraints. The fitness is then the
    sum of weighted travel distances across all sub-routes, where each sub-route
    starts and ends at the depot.

    Parameters:
    - depot (Depot): The starting and ending point of every sub-route.
    - route (List[DeliveryNode]): Flat ordered list of all delivery nodes.
    - vehicles (VehicleConfig): Fleet configuration holding capacity, max_range and
                                count.

    Returns:
    float: Total weighted travel distance across all sub-routes. Lower is better.
    """
    sub_routes = split_route_into_vehicles(depot, route, vehicles)

    total_cost = 0.0
    for sub in sub_routes:
        # depot → nodes → depot distance for this sub-route
        total_cost += _weighted_route_distance(depot, sub)

    return total_cost


def sort_population(
    population: List[List[DeliveryNode]], fitness: List[float]
) -> Tuple[List[List[DeliveryNode]], List[float]]:
    """
    Sort a population based on fitness values in ascending order.

    Parameters:
    - population (List[List[DeliveryNode]]): The population of routes, where each route
                                             is a list of delivery nodes.
    - fitness (List[float]): The corresponding fitness values for each route in the
                             population.

    Returns:
    Tuple[List[List[DeliveryNode]], List[float]]: The population sorted by ascending
                                                  fitness, along with the sorted fitness
                                                  values.
    """
    # Combine lists into pairs
    combined_lists = list(zip(population, fitness))

    # Sort based on the values of the fitness list
    sorted_combined_lists = sorted(combined_lists, key=lambda x: x[1])

    # Separate the sorted pairs back into individual lists
    sorted_population, sorted_fitness = zip(*sorted_combined_lists)

    return list(sorted_population), list(sorted_fitness)


def order_crossover(
    parent1: List[DeliveryNode], parent2: List[DeliveryNode]
) -> List[DeliveryNode]:
    """
    Perform order crossover (OX) between two parent routes to create a child route.
    A random segment is copied from parent1, and the remaining nodes are filled
    in the order they appear in parent2.

    Parameters:
    - parent1 (List[DeliveryNode]): The first parent route.
    - parent2 (List[DeliveryNode]): The second parent route.

    Returns:
    List[DeliveryNode]: The child route resulting from the order crossover.
    """
    length = len(parent1)

    # Choose two random indices for the crossover
    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    # Initialize the child with a copy of the substring from parent1
    child = parent1[start_index:end_index]

    # Fill in the remaining positions with genes from parent2
    remaining_positions = [
        i for i in range(length) if i < start_index or i >= end_index
    ]
    remaining_genes = [gene for gene in parent2 if gene not in child]

    for position, gene in zip(remaining_positions, remaining_genes):
        child.insert(position, gene)

    return child


def mutate(
    solution: List[DeliveryNode],
    mutation_probability: float,
    mutation_intensity: float = 0.2,
) -> List[DeliveryNode]:
    """
    Mutate a route by inverting a random segment of the sequence.

    Parameters:
    - solution (List[DeliveryNode]): The route to be mutated.
    - mutation_probability (float): The probability of mutation occurring (0.0 to 1.0).
    - mutation_intensity (float): Controls the relative size of the inverted segment
                                  (0.0 to 1.0). E.g. 0.2 means up to 20% of the route
                                  length is inverted.

    Returns:
    List[DeliveryNode]: The mutated route, with a segment reversed if mutation occurred.
    """
    mutated_solution = copy.deepcopy(solution)

    # Check if mutation should occur
    if random.random() < mutation_probability:
        n = len(solution)
        if n < 2:
            return solution

        # Determine max segment length based on intensity, at least 2 elements
        max_segment_len = max(2, int(n * mutation_intensity))

        # Pick a random start index and segment length
        segment_len = random.randint(2, max_segment_len)
        start = random.randint(0, n - segment_len)
        end = start + segment_len  # exclusive

        # Invert (reverse) the segment in place
        mutated_solution[start:end] = mutated_solution[start:end][::-1]

    return mutated_solution
