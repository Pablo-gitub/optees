from __future__ import annotations

import pytest

from optees.application.usecases.solve_multi_dimensional_knapsack_usecase import (
    SolveMultiDimensionalKnapsackUseCase,
)
from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class RecordingMultiDimensionalKnapsackPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 22.0,
            "selected_indices": [0, 2],
            "x": {"A": 1.0, "B": 0.0, "C": 1.0, "D": 0.0},
            "extras": {
                "method": "multidimensional_branch_and_bound",
                "complexity": "O(2^n * m)",
                "item_count": 4,
                "resource_count": 2,
            },
        }


def _small_model() -> MultiDimensionalKnapsackModel:
    return MultiDimensionalKnapsackModel.from_parts(
        (
            MultiDimensionalKnapsackResource("weight", 10),
            MultiDimensionalKnapsackResource("volume", 6),
        ),
        (
            MultiDimensionalKnapsackItem("A", value=8, resource_usage=(4, 1.5)),
            MultiDimensionalKnapsackItem("B", value=9, resource_usage=(5, 2)),
            MultiDimensionalKnapsackItem("C", value=14, resource_usage=(6, 4.5)),
            MultiDimensionalKnapsackItem("D", value=7, resource_usage=(3, 2)),
        ),
    )


def test_usecase_maps_model_to_canonical_problem_and_solution():
    port = RecordingMultiDimensionalKnapsackPort()
    usecase = SolveMultiDimensionalKnapsackUseCase(port)

    solution = usecase.execute(_small_model())

    assert port.problem == {
        "values": [8.0, 9.0, 14.0, 7.0],
        "usage_matrix": [
            [4.0, 1.5],
            [5.0, 2.0],
            [6.0, 4.5],
            [3.0, 2.0],
        ],
        "capacities": [10.0, 6.0],
        "var_names": ["A", "B", "C", "D"],
        "resource_names": ["weight", "volume"],
    }
    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(22.0)
    assert solution.selected_indices == (0, 2)
    assert solution.selected_item_names == ("A", "C")
    assert solution.total_value == pytest.approx(22.0)
    assert solution.resource_usage_totals == pytest.approx((10.0, 6.0))
    assert solution.remaining_capacities == pytest.approx((0.0, 0.0))
    assert solution.diagnostics.method == "multidimensional_branch_and_bound"


def test_usecase_normalizes_missing_selection_to_empty_solution():
    class MissingSelectionPort:
        def solve(self, problem):
            return {
                "status": "NotSolved",
                "objective": None,
                "extras": {"method": "multidimensional_branch_and_bound"},
            }

    solution = SolveMultiDimensionalKnapsackUseCase(MissingSelectionPort()).execute(
        _small_model()
    )

    assert solution.status is KnapsackSolveStatus.NOT_SOLVED
    assert solution.selected_indices == ()
    assert solution.total_value == pytest.approx(0.0)
    assert solution.resource_usage_totals == pytest.approx((0.0, 0.0))
    assert solution.remaining_capacities == pytest.approx((10.0, 6.0))

