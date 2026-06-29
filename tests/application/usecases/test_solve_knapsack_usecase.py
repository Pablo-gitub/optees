from __future__ import annotations

import pytest

from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack_model import KnapsackModel
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


class RecordingKnapsackPort:
    def __init__(self):
        self.problem = None

    def solve(self, problem):
        self.problem = problem
        return {
            "status": "Optimal",
            "objective": 7.0,
            "selected_indices": [0, 1],
            "x": {"A": 1.0, "B": 1.0, "C": 0.0},
            "extras": {
                "method": "dynamic_programming",
                "complexity": "O(n * capacity)",
                "item_count": 3,
                "capacity": 5,
            },
        }


def _small_model() -> KnapsackModel:
    return KnapsackModel.from_parts(
        (
            KnapsackItem("A", 3, 2),
            KnapsackItem("B", 4, 3),
            KnapsackItem("C", 5, 4),
        ),
        capacity=5,
    )


def test_usecase_maps_model_to_canonical_problem_and_solution():
    port = RecordingKnapsackPort()
    usecase = SolveKnapsackUseCase(port)

    solution = usecase.execute(_small_model())

    assert port.problem == {
        "values": [3.0, 4.0, 5.0],
        "weights": [2, 3, 4],
        "capacity": 5,
        "var_names": ["A", "B", "C"],
    }
    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(7.0)
    assert solution.selected_indices == (0, 1)
    assert solution.selected_item_names == ("A", "B")
    assert solution.total_value == pytest.approx(7.0)
    assert solution.total_weight == 5
    assert solution.remaining_capacity == 0
    assert solution.diagnostics.method == "dynamic_programming"


def test_model_is_immutable_when_updating_items():
    model = _small_model()

    updated = model.set_item_value(0, 10).set_item_weight(1, 1)

    assert model.item(0).value == pytest.approx(3.0)
    assert model.item(1).weight == 3
    assert updated.item(0).value == pytest.approx(10.0)
    assert updated.item(1).weight == 1


def test_domain_rejects_invalid_capacity_and_weight():
    with pytest.raises(ValueError):
        KnapsackModel.from_parts([], capacity=2.5)

    with pytest.raises(ValueError):
        KnapsackItem("bad", 1.0, 2.5)
