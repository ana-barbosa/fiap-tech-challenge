import itertools
import random
import sys
from pathlib import Path

import numpy as np
import pygame
import tomli_w
import tomllib

from .constants import (
    CONVERGENCE_PATIENCE,
    CONVERGENCE_THRESHOLD,
    FPS,
    GRAY,
    MAX_RUNTIME_SECONDS,
    MUTATION_PROBABILITY,
    POPULATION_SIZE,
    VEHICLE_COLORS,
    WHITE,
)
from .draw_functions import draw_cities, draw_plot, draw_vrp_routes, init_screen
from .genetic_algorithm import (
    calculate_fitness,
    generate_random_population,
    mutate,
    order_crossover,
    sort_population,
    split_route_into_vehicles,
)
from .models import ProblemInput, Route, Solution
from .stopping import StoppingCondition


def _save_solution(
    input_path: Path,
    problem: ProblemInput,
    best_sub_routes,
    best_fitness: float,
    stopping_condition: StoppingCondition,
    output_dir: Path = Path("output"),
) -> None:
    solution = Solution(
        best_fitness=best_fitness,
        stopping_reason=stopping_condition.reason,
        depot=problem.depot,
        vehicles=problem.vehicles,
        routes=[
            Route(vehicle_index=i, depot=problem.depot, nodes=sub)
            for i, sub in enumerate(best_sub_routes)
        ],
    )

    output_path = output_dir / input_path.name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        tomli_w.dump(solution.model_dump(), f)

    print(f"Best solution saved to {output_path}")


def run(input_path: Path, generations: int | None = None) -> None:
    """
    Run the VRP genetic algorithm planner.

    Parameters:
    - input_path (Path): Path to the TOML problem file.
    - generations (int | None): Fixed generation cap. Overrides convergence/time limit.
    """
    with open(input_path, "rb") as f:
        problem = ProblemInput.model_validate(tomllib.load(f))

    # Initialize Pygame
    screen = init_screen()
    clock = pygame.time.Clock()
    generation_counter = itertools.count(start=1)  # Start the counter at 1

    # Initialize stopping condition
    stopping_condition = StoppingCondition(
        max_seconds=MAX_RUNTIME_SECONDS,
        patience=CONVERGENCE_PATIENCE,
        threshold=CONVERGENCE_THRESHOLD,
        generations=generations,
    )

    # Create Initial Population
    population = generate_random_population(
        problem.depot, problem.deliveries, POPULATION_SIZE
    )
    best_fitness_values = []

    # Main game loop
    running = True
    while running and not stopping_condition.should_stop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False

        generation = next(generation_counter)

        screen.fill(WHITE)

        population_fitness = [
            calculate_fitness(problem.depot, individual, problem.vehicles)
            for individual in population
        ]
        population, population_fitness = sort_population(population, population_fitness)

        best_fitness = population_fitness[0]
        best_fitness_values.append(best_fitness)
        stopping_condition.update(best_fitness)

        if stopping_condition.has_improved:
            print(f"Generation {generation}: Best fitness = {round(best_fitness, 2)}")

        draw_plot(screen, best_fitness_values, y_label="Fitness - Distance")
        draw_cities(screen, problem.depot, problem.deliveries)

        # best solution
        best_sub_routes = split_route_into_vehicles(
            problem.depot, population[0], problem.vehicles
        )
        draw_vrp_routes(
            screen,
            problem.depot,
            problem.deliveries,
            best_sub_routes,
            VEHICLE_COLORS,
            line_width=3,
        )

        # second best solution
        second_sub_routes = split_route_into_vehicles(
            problem.depot, population[1], problem.vehicles
        )
        draw_vrp_routes(
            screen,
            problem.depot,
            problem.deliveries,
            second_sub_routes,
            [GRAY],
            line_width=1,
        )

        new_population = [population[0]]  # Keep the best individual: ELITISM

        while len(new_population) < POPULATION_SIZE:
            # solution based on fitness probability
            probability = 1 / np.array(population_fitness)
            parent1, parent2 = random.choices(
                population, weights=probability.tolist(), k=2
            )

            child = order_crossover(parent1, parent2)

            child = mutate(child, MUTATION_PROBABILITY)

            new_population.append(child)

        population = new_population

        pygame.display.flip()
        clock.tick(FPS)

    print(f"Stopped: {stopping_condition.reason}")

    _save_solution(
        input_path, problem, best_sub_routes, best_fitness, stopping_condition
    )

    pygame.quit()
    sys.exit()
