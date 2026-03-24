import unittest

from src.draw_functions import _scale_locations
from src.models import DeliveryNode, Depot


def make_depot(lat: float, lon: float) -> Depot:
    return Depot(location=(lat, lon))


def make_node(lat: float, lon: float) -> DeliveryNode:
    return DeliveryNode(location=(lat, lon), demand=10.0)


class TestScaleLocations(unittest.TestCase):
    def test_depot_scales_correctly(self):
        # depot at min lat/lon, node at max lat/lon
        # depot should be bottom-left (high y, low x), node top-right (low y, high x)
        depot = make_depot(0.0, 0.0)
        nodes = [make_node(10.0, 10.0)]
        scaled_depot, scaled_nodes = _scale_locations(depot, nodes)
        self.assertLess(scaled_depot[0], scaled_nodes[0][0])  # depot x < node x
        self.assertGreater(
            scaled_depot[1], scaled_nodes[0][1]
        )  # depot y > node y (south = lower on screen)

    def test_north_is_up(self):
        # Higher latitude should map to lower y (closer to top of screen)
        depot = make_depot(0.0, 0.0)
        node_north = make_node(10.0, 5.0)
        node_south = make_node(1.0, 5.0)
        _, scaled = _scale_locations(depot, [node_north, node_south])
        self.assertLess(scaled[0][1], scaled[1][1])  # north y < south y

    def test_east_is_right(self):
        # Higher longitude should map to higher x (right side of screen)
        depot = make_depot(0.0, 0.0)  # different lat from nodes
        node_east = make_node(5.0, 10.0)
        node_west = make_node(5.0, 1.0)
        _, scaled = _scale_locations(depot, [node_east, node_west])
        self.assertGreater(scaled[0][0], scaled[1][0])  # east x > west x

    def test_negative_coordinates_handled(self):
        # lat/lon can be negative (e.g. Brazil, southern US)
        depot = make_depot(-15.78, -47.93)
        nodes = [make_node(-23.55, -46.63), make_node(-3.72, -38.54)]
        scaled_depot, scaled_nodes = _scale_locations(depot, nodes)
        # All scaled values should be non-negative integers on screen
        self.assertGreaterEqual(scaled_depot[0], 0)
        self.assertGreaterEqual(scaled_depot[1], 0)
        for sx, sy in scaled_nodes:
            self.assertGreaterEqual(sx, 0)
            self.assertGreaterEqual(sy, 0)

    def test_returns_correct_number_of_scaled_nodes(self):
        depot = make_depot(0.0, 0.0)
        nodes = [make_node(float(i), float(i)) for i in range(1, 6)]
        _, scaled_nodes = _scale_locations(depot, nodes)
        self.assertEqual(len(scaled_nodes), len(nodes))

    def test_relative_order_preserved_longitude(self):
        # Nodes ordered west to east should have increasing x values
        depot = make_depot(5.0, -10.0)  # distinct lat to avoid division by zero
        nodes = [make_node(0.0, float(i)) for i in range(5)]
        _, scaled_nodes = _scale_locations(depot, nodes)
        x_values = [s[0] for s in scaled_nodes]
        self.assertEqual(x_values, sorted(x_values))

    def test_relative_order_preserved_latitude(self):
        # Nodes ordered south to north should have decreasing y values
        depot = make_depot(-10.0, 5.0)  # distinct lon to avoid division by zero
        nodes = [make_node(float(i), 0.0) for i in range(5)]
        _, scaled_nodes = _scale_locations(depot, nodes)
        y_values = [s[1] for s in scaled_nodes]
        self.assertEqual(y_values, sorted(y_values, reverse=True))
