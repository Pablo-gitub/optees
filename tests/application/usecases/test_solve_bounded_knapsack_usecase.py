from __future__ import annotations

import pytest

from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class RecordingBoundedKnapsackPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 22.0,
            "quantities": [2, 1],
            "x": {"A": 2, "B": 1},
            "extras": {
                "method": "bounded_dynamic_programming",
                "complexity": "O(capacity * sum_i feasible_quantity_i)",
                "item_count": 2,
                "capacity": 7,
                "dp_cells": 48,
                "max_dp_cells": 5_000_000,
            },
        }


def _small_model() -> BoundedKnapsackModel:
    return BoundedKnapsackModel.from_parts(
        (
            BoundedKnapsackItem("A", value=6, weight=2, max_quantity=3),
            BoundedKnapsackItem("B", value=10, weight=3, max_quantity=2),
        ),
        capacity=7,
    )


def test_usecase_maps_model_to_canonical_problem_and_solution():
    port = RecordingBoundedKnapsackPort()
    usecase = SolveBoundedKnapsackUseCase(port)

    solution = usecase.execute(_small_model())

    assert port.problem == {
        "values": [6.0, 10.0],
        "weights": [2, 3],
        "max_quantities": [3, 2],
        "capacity": 7,
        "var_names": ["A", "B"],
    }
    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(22.0)
    assert solution.quantities == (2, 1)
    assert solution.selected_indices == (0, 1)
    assert solution.selected_item_names == ("A", "B")
    assert solution.total_value == pytest.approx(22.0)
    assert solution.total_weight == 7
    assert solution.remaining_capacity == 0
    assert solution.diagnostics.method == "bounded_dynamic_programming"
    assert solution.diagnostics.dp_cells == 48


def test_usecase_normalizes_missing_quantities_to_empty_selection():
    class MissingQuantityPort:
        def solve(self, problem):
            return {
                "status": "NotSolved",
                "objective": None,
                "extras": {"method": "bounded_dynamic_programming"},
            }

    solution = SolveBoundedKnapsackUseCase(MissingQuantityPort()).execute(_small_model())

    assert solution.status is KnapsackSolveStatus.NOT_SOLVED
    assert solution.quantities == (0, 0)
    assert solution.selected_indices == ()
    assert solution.total_value == pytest.approx(0.0)
    assert solution.total_weight == 0

