from typing import List, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pygame
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .constants import (
    DARK_GRAY,
    GREEN,
    HEIGHT,
    NODE_RADIUS,
    ORANGE,
    PADDING,
    PLOT_X_OFFSET,
    WIDTH,
)
from .models import DeliveryNode, Depot

matplotlib.use("Agg")


def _scale_locations(
    depot: Depot, deliveries: List[DeliveryNode]
) -> Tuple[Tuple[int, int], List[Tuple[int, int]]]:
    """
    Scale depot and delivery locations to fit the drawable area of the Pygame screen.
    Works correctly with lat/lon coordinates: lon maps to x, lat maps to y (flipped
    so north is up).
    """
    raw_locations = [node.location for node in deliveries]
    all_points = [depot.location] + raw_locations

    min_lat = min(p[0] for p in all_points)
    max_lat = max(p[0] for p in all_points)
    min_lon = min(p[1] for p in all_points)
    max_lon = max(p[1] for p in all_points)

    draw_width = WIDTH - PLOT_X_OFFSET - 2 * PADDING
    draw_height = HEIGHT - 2 * PADDING

    scale_x = draw_width / (max_lon - min_lon)
    scale_y = draw_height / (max_lat - min_lat)

    def scale(p: Tuple[float, float]) -> Tuple[int, int]:
        return (
            int((p[1] - min_lon) * scale_x + PLOT_X_OFFSET + PADDING),  # lon → x
            int((max_lat - p[0]) * scale_y + PADDING),  # lat → y (flipped)
        )

    return scale(depot.location), [scale(p) for p in raw_locations]


def init_screen() -> pygame.Surface:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TSP Solver using Pygame")
    return screen


def draw_plot(
    screen: pygame.Surface,
    fitness_values: list,
    x_label: str = "Generation",
    y_label: str = "Fitness",
) -> None:
    """
    Draw a plot on a Pygame screen using Matplotlib.

    Parameters:
    - screen (pygame.Surface): The Pygame surface to draw the plot on.
    - fitness_values (list): The fitness value recorded at each generation, plotted
                             on the y-axis. The x-axis is automatically set to the
                             generation index.
    - x_label (str): Label for the x-axis (default is 'Generation').
    - y_label (str): Label for the y-axis (default is 'Fitness').
    """
    x = list(range(len(fitness_values)))
    y = fitness_values

    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.plot(x, y)
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()

    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    screen.blit(surf, (0, 0))
    plt.close(fig)


def draw_cities(
    screen: pygame.Surface, depot: Depot, deliveries: List[DeliveryNode]
) -> None:
    """
    Draw delivery nodes and depot on the Pygame screen.

    Parameters:
    - screen: the Pygame surface to draw on.
    - depot: the depot node, drawn in green and slightly larger.
    - deliveries: list of delivery nodes; critical nodes in orange, regular in dark
                  gray.
    """
    scaled_depot, scaled_deliveries = _scale_locations(depot, deliveries)

    for node, location in zip(deliveries, scaled_deliveries):
        color = ORANGE if node.priority == "critical" else DARK_GRAY
        pygame.draw.circle(screen, color, location, NODE_RADIUS)

    pygame.draw.circle(screen, GREEN, scaled_depot, NODE_RADIUS + 2)


def _draw_paths(
    screen: pygame.Surface,
    depot: Depot,
    deliveries: List[DeliveryNode],
    route: List[DeliveryNode],
    rgb_color: Tuple[int, int, int],
    line_width: int,
) -> None:
    scaled_depot, scaled_deliveries = _scale_locations(depot, deliveries)
    node_to_scaled = {
        node.location: scaled_deliveries[i] for i, node in enumerate(deliveries)
    }
    path_locations = (
        [scaled_depot]
        + [node_to_scaled[node.location] for node in route]
        + [scaled_depot]
    )

    pygame.draw.lines(screen, rgb_color, False, path_locations, width=line_width)


def draw_vrp_routes(
    screen: pygame.Surface,
    depot: Depot,
    deliveries: List[DeliveryNode],
    sub_routes: List[List[DeliveryNode]],
    colors: List[Tuple[int, int, int]],
    line_width: int = 1,
) -> None:
    """
    Draw all VRP sub-routes on the Pygame screen, each in a distinct colour.

    Parameters:
    - screen: the Pygame surface to draw on.
    - depot: the starting and ending point of every sub-route.
    - deliveries: full list of delivery nodes (used as scaling reference).
    - sub_routes: list of sub-routes, one per vehicle.
    - colors: list of RGB colours, one per sub-route (cycles if fewer than sub-routes).
    - line_width: width of the path lines.
    """
    for i, sub in enumerate(sub_routes):
        color = colors[i % len(colors)]
        _draw_paths(
            screen, depot, deliveries, sub, rgb_color=color, line_width=line_width
        )
