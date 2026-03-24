import time

from pydantic import BaseModel, Field


class StoppingCondition(BaseModel):
    """
    Determines when the GA should stop evolving.

    Priority order:
    1. Fixed generations — if provided, runs exactly N generations and stops.
    2. Convergence — stops if fitness hasn't improved by more than threshold
                     over the last `patience` generations.
    3. Time limit — hard fallback, stops after max_seconds regardless.

    Parameters:
    - max_seconds (int): Hard time limit in seconds.
    - patience (int): Generations without improvement before convergence is declared.
    - threshold (float): Minimum relative improvement to count as progress (0.0 to 1.0).
    - generations (int | None): If provided, overrides everything else.
    """

    max_seconds: int = Field(gt=0)
    patience: int = Field(gt=0)
    threshold: float = Field(ge=0.0)
    generations: int | None = Field(default=None, gt=0)

    # Private mutable state, excluded from serialisation
    _start_time: float = 0.0
    _best_fitness: float = float("inf")
    _generations_without_improvement: int = 0
    _current_generation: int = 0

    def model_post_init(self, __context) -> None:
        self._start_time = time.time()
        self._best_fitness = float("inf")
        self._generations_without_improvement = 0
        self._current_generation = 0

    def update(self, fitness: float) -> None:
        """
        Update stopping condition state with the best fitness of the current generation.
        Must be called once per generation.

        Parameters:
        - fitness (float): The best fitness value in the current generation.
        """
        self._current_generation += 1
        improvement = self._best_fitness - fitness

        if improvement > self.threshold:
            self._best_fitness = fitness
            self._generations_without_improvement = 0
        else:
            self._generations_without_improvement += 1

    @property
    def has_improved(self) -> bool:
        return self._generations_without_improvement == 0

    @property
    def should_stop(self) -> bool:
        """Returns True when any stopping condition is met."""
        if self.generations is not None:
            return self._current_generation >= self.generations

        if time.time() - self._start_time >= self.max_seconds:
            return True

        if self._generations_without_improvement >= self.patience:
            return True

        return False

    @property
    def reason(self) -> str:
        """Human-readable explanation of why the GA stopped."""
        if self.generations is not None:
            return f"Reached fixed generation limit of {self.generations}"
        if time.time() - self._start_time >= self.max_seconds:
            return f"Reached time limit of {self.max_seconds}s"
        return (
            f"Converged after {self._current_generation} "
            f"generations without improvement"
        )
