from __future__ import annotations

import pytest

from optees.application.usecases.solve_fractional_knapsack_usecase import (
    SolveFractionalKnapsackUseCase,
)
from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class RecordingFractionalKnapsackPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 240.0,
            "fractions": [1.0, 1.0, 2.0 / 3.0],
            "x": {"A": 1.0, "B": 1.0, "C": 2.0 / 3.0},
            "extras": {
                "method": "fractional_greedy_density",
                "complexity": "O(n log n)",
                "item_count": 3,
                "capacity": 50.0,
            },
        }


def _classic_model() -> FractionalKnapsackModel:
    return FractionalKnapsackModel.from_parts(
        (
            FractionalKnapsackItem("A", value=60, weight=10),
            FractionalKnapsackItem("B", value=100, weight=20),
            FractionalKnapsackItem("C", value=120, weight=30),
        ),
        capacity=50,
    )


def test_usecase_maps_model_to_canonical_problem_and_solution():
    port = RecordingFractionalKnapsackPort()
    usecase = SolveFractionalKnapsackUseCase(port)

    solution = usecase.execute(_classic_model())

    assert port.problem == {
        "values": [60.0, 100.0, 120.0],
        "weights": [10.0, 20.0, 30.0],
        "capacity": 50.0,
        "var_names": ["A", "B", "C"],
    }
    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(240.0)
    assert solution.fractions == pytest.approx((1.0, 1.0, 2.0 / 3.0))
    assert solution.selected_indices == (0, 1, 2)
    assert solution.selected_item_names == ("A", "B", "C")
    assert solution.total_value == pytest.approx(240.0)
    assert solution.total_weight == pytest.approx(50.0)
    assert solution.remaining_capacity == pytest.approx(0.0)
    assert solution.diagnostics.method == "fractional_greedy_density"


def test_usecase_normalizes_missing_fractions_to_empty_selection():
    class MissingFractionsPort:
        def solve(self, problem):
            return {
                "status": "NotSolved",
                "objective": None,
                "extras": {"method": "fractional_greedy_density"},
            }

    solution = SolveFractionalKnapsackUseCase(MissingFractionsPort()).execute(
        _classic_model()
    )

    assert solution.status is KnapsackSolveStatus.NOT_SOLVED
    assert solution.fractions == (0.0, 0.0, 0.0)
    assert solution.selected_indices == ()
    assert solution.total_value == pytest.approx(0.0)
    assert solution.total_weight == pytest.approx(0.0)

