from __future__ import annotations

import pytest

from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class RecordingUnboundedKnapsackPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 110.0,
            "quantities": [0, 1, 0, 1],
            "x": {"A": 0, "B": 1, "C": 0, "D": 1},
            "extras": {
                "method": "unbounded_dynamic_programming",
                "complexity": "O(n * capacity)",
                "item_count": 4,
                "capacity": 8,
                "dp_cells": 36,
                "max_dp_cells": 5_000_000,
            },
        }


def _small_model() -> UnboundedKnapsackModel:
    return UnboundedKnapsackModel.from_parts(
        (
            UnboundedKnapsackItem("A", value=10, weight=1),
            UnboundedKnapsackItem("B", value=40, weight=3),
            UnboundedKnapsackItem("C", value=50, weight=4),
            UnboundedKnapsackItem("D", value=70, weight=5),
        ),
        capacity=8,
    )


def test_usecase_maps_model_to_canonical_problem_and_solution():
    port = RecordingUnboundedKnapsackPort()
    usecase = SolveUnboundedKnapsackUseCase(port)

    solution = usecase.execute(_small_model())

    assert port.problem == {
        "values": [10.0, 40.0, 50.0, 70.0],
        "weights": [1, 3, 4, 5],
        "capacity": 8,
        "var_names": ["A", "B", "C", "D"],
    }
    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(110.0)
    assert solution.quantities == (0, 1, 0, 1)
    assert solution.selected_indices == (1, 3)
    assert solution.selected_item_names == ("B", "D")
    assert solution.total_value == pytest.approx(110.0)
    assert solution.total_weight == 8
    assert solution.remaining_capacity == 0
    assert solution.diagnostics.method == "unbounded_dynamic_programming"
    assert solution.diagnostics.dp_cells == 36


def test_usecase_preserves_unbounded_status():
    class UnboundedPort:
        def solve(self, problem):
            return {
                "status": "Unbounded",
                "objective": None,
                "extras": {
                    "method": "unbounded_dynamic_programming",
                    "message": "zero-weight item with positive value",
                },
            }

    model = UnboundedKnapsackModel.from_parts(
        (UnboundedKnapsackItem("Free", value=1, weight=0),),
        capacity=5,
    )

    solution = SolveUnboundedKnapsackUseCase(UnboundedPort()).execute(model)

    assert solution.status is KnapsackSolveStatus.UNBOUNDED
    assert solution.is_unbounded()
    assert solution.objective is None
    assert solution.quantities == (0,)
    assert solution.diagnostics.message == "zero-weight item with positive value"

