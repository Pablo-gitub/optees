from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.data.adapters.knapsack.knapsack_solver_adapter import KnapsackSolverAdapter
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack_model import KnapsackModel
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus
from optees.utility.data_adapters.knapsack_burkardt_adapter import (
    load_knapsack_burkardt,
)

DATA_ROOT = Path("tests/data/knapsack")


def _model_from_burkardt(instance: str) -> tuple[KnapsackModel, list[int]]:
    data = load_knapsack_burkardt(str(DATA_ROOT / instance), instance)
    items = tuple(
        KnapsackItem(f"{instance}_item_{i + 1}", value, weight)
        for i, (value, weight) in enumerate(zip(data["values"], data["weights"]))
    )
    return KnapsackModel.from_parts(items, capacity=data["capacity"]), data["opt_selection"]


@pytest.mark.parametrize("instance", ["p01", "p02"])
def test_usecase_solves_small_burkardt_instances(instance):
    model, opt_selection = _model_from_burkardt(instance)
    expected_indices = tuple(i for i, selected in enumerate(opt_selection) if selected == 1)

    solution = SolveKnapsackUseCase(KnapsackSolverAdapter()).execute(model)

    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.selected_indices == expected_indices
    assert solution.total_weight <= model.capacity
    assert solution.objective == pytest.approx(solution.total_value)


def test_usecase_reports_large_burkardt_instance_outside_dp_budget():
    model, _ = _model_from_burkardt("p08")

    solution = SolveKnapsackUseCase(
        KnapsackSolverAdapter(max_dp_cells=1_000_000)
    ).execute(model)

    assert solution.status is KnapsackSolveStatus.NOT_SOLVED
    assert solution.selected_indices == ()
    assert solution.diagnostics.method == "dynamic_programming"
    assert solution.diagnostics.dp_cells > solution.diagnostics.max_dp_cells
    assert "too large" in solution.diagnostics.message

