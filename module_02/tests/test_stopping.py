import time
import unittest
from typing import Any

from src.stopping import StoppingCondition


def make_stopping(**overrides) -> StoppingCondition:
    """Helper to build a valid StoppingCondition with sensible defaults."""
    base: dict[str, Any] = {
        "max_seconds": 60,
        "patience": 10,
        "threshold": 0.0,
        "generations": None,
    }
    base.update(overrides)
    return StoppingCondition(**base)


class TestHasImproved(unittest.TestCase):
    def test_true_on_first_update(self):
        sc = make_stopping()
        sc.update(100.0)
        self.assertTrue(sc.has_improved)

    def test_true_when_fitness_improves(self):
        sc = make_stopping()
        sc.update(100.0)
        sc.update(90.0)
        self.assertTrue(sc.has_improved)

    def test_false_when_fitness_does_not_improve(self):
        sc = make_stopping()
        sc.update(100.0)
        sc.update(100.0)
        self.assertFalse(sc.has_improved)

    def test_false_when_fitness_gets_worse(self):
        sc = make_stopping()
        sc.update(100.0)
        sc.update(110.0)
        self.assertFalse(sc.has_improved)

    def test_true_again_after_improvement_following_stagnation(self):
        sc = make_stopping()
        sc.update(100.0)
        sc.update(100.0)  # no improvement
        sc.update(90.0)  # improvement
        self.assertTrue(sc.has_improved)

    def test_below_threshold_not_counted_as_improvement(self):
        sc = make_stopping(threshold=5.0)
        sc.update(100.0)
        sc.update(96.0)  # improvement of 4.0 < threshold of 5.0
        self.assertFalse(sc.has_improved)

    def test_above_threshold_counted_as_improvement(self):
        sc = make_stopping(threshold=5.0)
        sc.update(100.0)
        sc.update(94.0)  # improvement of 6.0 > threshold of 5.0
        self.assertTrue(sc.has_improved)


class TestShouldStopFixedGenerations(unittest.TestCase):
    def test_does_not_stop_before_limit(self):
        sc = make_stopping(generations=3)
        sc.update(100.0)
        sc.update(90.0)
        self.assertFalse(sc.should_stop)

    def test_stops_at_exact_generation_limit(self):
        sc = make_stopping(generations=3)
        sc.update(100.0)
        sc.update(90.0)
        sc.update(80.0)
        self.assertTrue(sc.should_stop)

    def test_fixed_generations_overrides_convergence(self):
        # patience=2 would stop after 2 non-improving generations,
        # but generations=10 should keep it running
        sc = make_stopping(generations=10, patience=2)
        for _ in range(9):
            sc.update(100.0)  # no improvement after first
        self.assertFalse(sc.should_stop)

    def test_fixed_generations_overrides_time_limit(self):
        sc = make_stopping(generations=5, max_seconds=1)
        time.sleep(1.1)  # exceed time limit
        for _ in range(4):
            sc.update(100.0)
        self.assertFalse(sc.should_stop)  # generations not reached yet


class TestShouldStopConvergence(unittest.TestCase):
    def test_does_not_stop_before_patience_exhausted(self):
        sc = make_stopping(patience=5)
        sc.update(100.0)
        for _ in range(4):
            sc.update(100.0)  # 4 non-improving generations
        self.assertFalse(sc.should_stop)

    def test_stops_after_patience_exhausted(self):
        sc = make_stopping(patience=5)
        sc.update(100.0)
        for _ in range(5):
            sc.update(100.0)  # 5 non-improving generations
        self.assertTrue(sc.should_stop)

    def test_patience_resets_on_improvement(self):
        sc = make_stopping(patience=3)
        sc.update(100.0)
        sc.update(100.0)  # 1 non-improving
        sc.update(100.0)  # 2 non-improving
        sc.update(90.0)  # improvement — resets counter
        sc.update(90.0)  # 1 non-improving
        sc.update(90.0)  # 2 non-improving
        self.assertFalse(sc.should_stop)  # only 2, not yet 3


class TestShouldStopTimeLimit(unittest.TestCase):
    def test_does_not_stop_before_time_limit(self):
        sc = make_stopping(max_seconds=60)
        sc.update(100.0)
        self.assertFalse(sc.should_stop)

    def test_stops_after_time_limit(self):
        sc = make_stopping(max_seconds=1)
        sc.update(100.0)
        time.sleep(1.1)
        self.assertTrue(sc.should_stop)


class TestReason(unittest.TestCase):
    def test_reason_fixed_generations(self):
        sc = make_stopping(generations=2)
        sc.update(100.0)
        sc.update(90.0)
        self.assertIn("2", sc.reason)

    def test_reason_convergence(self):
        sc = make_stopping(patience=3)
        sc.update(100.0)
        for _ in range(3):
            sc.update(100.0)
        self.assertIn("Converged", sc.reason)

    def test_reason_time_limit(self):
        sc = make_stopping(max_seconds=1)
        sc.update(100.0)
        time.sleep(1.1)
        self.assertIn("time limit", sc.reason)
