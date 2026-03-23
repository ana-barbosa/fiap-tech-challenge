from __future__ import annotations

import math
from typing import List, Literal, Tuple

from pydantic import BaseModel, Field, model_serializer, model_validator


class Location(BaseModel):
    """
    Base class for any entity with a physical position on the map.
    Provides shared distance calculation logic.
    """

    location: Tuple[float, float]

    def distance_to(self, other: Location) -> float:
        """Return the Euclidean distance between this location and another."""
        return math.sqrt(
            (self.location[0] - other.location[0]) ** 2
            + (self.location[1] - other.location[1]) ** 2
        )


class Depot(Location):
    """
    The starting and ending point for all vehicle routes.
    Represents the warehouse, pharmacy, or distribution center.
    """

    pass


class DeliveryNode(Location):
    """
    A delivery stop with an associated demand and priority level.

    Attributes:
    - location: (lat, lon) coordinates of the delivery point.
    - priority: 'critical' for urgent medications, 'regular' for standard supplies.
    - demand: cargo units required for this delivery (must be > 0).
    """

    priority: Literal["critical", "regular"] = "regular"
    demand: float = Field(
        gt=0, description="Cargo units required, must be greater than 0."
    )


class VehicleConfig(BaseModel):
    """
    Configuration for the vehicle fleet. All vehicles are homogeneous in this version.

    Attributes:
    - count: number of vehicles available.
    - capacity: cargo capacity shared by all vehicles.
    - max_range: maximum range shared by all vehicles.
    """

    count: int = Field(gt=0, description="Number of vehicles in the fleet.")
    capacity: float = Field(gt=0)
    max_range: float = Field(gt=0)


class ProblemInput(BaseModel):
    """
    The full input definition for a VRP problem instance.
    Loaded from a TOML file provided by the user.

    Attributes:
    - depot: the warehouse/pharmacy location.
    - vehicles: fleet configuration.
    - deliveries: list of delivery nodes to be routed.
    """

    depot: Depot
    vehicles: VehicleConfig
    deliveries: List[DeliveryNode] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total_demand_feasible(self) -> ProblemInput:
        """Fail if the fleet cannot collectively serve all deliveries."""
        total_demand = sum(d.demand for d in self.deliveries)
        total_capacity = self.vehicles.capacity * self.vehicles.count
        if total_demand > total_capacity:
            raise ValueError(
                f"Total delivery demand ({total_demand}) exceeds total fleet "
                f"capacity ({total_capacity}). Add more vehicles or reduce demand."
            )
        return self

    @model_validator(mode="after")
    def validate_single_node_fits_capacity(self) -> ProblemInput:
        """Fail if any single delivery node exceeds vehicle capacity."""
        for node in self.deliveries:
            if node.demand > self.vehicles.capacity:
                raise ValueError(
                    f"Node at {node.location} has demand {node.demand} which exceeds "
                    f"vehicle capacity {self.vehicles.capacity}. No vehicle can ever "
                    f"serve it."
                )
        return self

    @model_validator(mode="after")
    def validate_depot_to_node_range_feasible(self) -> ProblemInput:
        """Fail if any node is unreachable and back within vehicle max range."""
        for node in self.deliveries:
            round_trip = 2 * self.depot.distance_to(node)
            if round_trip > self.vehicles.max_range:
                raise ValueError(
                    f"Node at {node.location} is unreachable: "
                    f"round trip distance {round(round_trip, 1)} "
                    f"exceeds vehicle max range {self.vehicles.max_range}."
                )
        return self


class Route(BaseModel):
    vehicle_index: int
    depot: Depot = Field(exclude=True)  # used only for distance calculation
    nodes: List[DeliveryNode]
    total_demand: float = 0.0
    total_distance_km: float = 0.0
    critical_stops: int = 0
    regular_stops: int = 0

    @model_validator(mode="after")
    def compute_route_stats(self) -> "Route":
        self.total_demand = round(sum(n.demand for n in self.nodes), 2)
        self.critical_stops = sum(1 for n in self.nodes if n.priority == "critical")
        self.regular_stops = sum(1 for n in self.nodes if n.priority == "regular")

        if self.nodes:
            distance = self.depot.distance_to(self.nodes[0])
            for i in range(len(self.nodes) - 1):
                distance += self.nodes[i].distance_to(self.nodes[i + 1])
            distance += self.nodes[-1].distance_to(self.depot)
            self.total_distance_km = round(distance * 111.0, 2)
        return self

    @model_serializer(mode="wrap")
    def ser(self, handler) -> dict:
        data = handler(self)
        for i, node in enumerate(data["nodes"]):
            # Add explicit order to delivery nodes, to make LLM fully aware
            node["stop_number"] = i + 1
        return data


class Solution(BaseModel):
    best_fitness: float
    stopping_reason: str
    depot: Depot
    vehicles: VehicleConfig
    routes: List[Route]
    total_vehicles_available: int = 0
    total_vehicles_used: int = 0
    total_demand_served: float = 0.0

    @model_validator(mode="after")
    def compute_solution_stats(self) -> "Solution":
        self.total_vehicles_available = self.vehicles.count
        self.total_vehicles_used = len(self.routes)
        self.total_demand_served = round(sum(r.total_demand for r in self.routes), 2)
        return self

    @model_serializer(mode="wrap")
    def ser(self, handler) -> dict:
        data = handler(self)
        # This information will be moved to root level, closer to total_vehicles_used
        data["vehicles"].pop("count")
        return data
