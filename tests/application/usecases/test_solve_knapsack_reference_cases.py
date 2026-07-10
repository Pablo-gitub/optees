from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
from optees.data.adapters.knapsack.bounded_knapsack_solver_adapter import (
    BoundedKnapsackSolverAdapter,
)
from optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter import (
    UnboundedKnapsackSolverAdapter,
)
from optees.domain.entities.knapsack.bounded_item import BoundedKnapsackItem
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.domain.value_objects.knapsack.solve_status import KnapsackSolveStatus


REFERENCE_CASES = json.loads(
    Path("tests/data/knapsack/reference_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", REFERENCE_CASES["bounded"], ids=lambda case: case["id"])
def test_bounded_solver_matches_documented_reference_case(case):
    model = BoundedKnapsackModel.from_parts(
        tuple(
            BoundedKnapsackItem(
                item["name"],
                item["value"],
                item["weight"],
                item["max_quantity"],
            )
            for item in case["items"]
        ),
        capacity=case["capacity"],
    )

    solution = SolveBoundedKnapsackUseCase(BoundedKnapsackSolverAdapter()).execute(model)

    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(case["expected_objective"])
    assert solution.quantities == tuple(case["expected_quantities"])
    assert solution.total_weight <= model.capacity


@pytest.mark.parametrize("case", REFERENCE_CASES["unbounded"], ids=lambda case: case["id"])
def test_unbounded_solver_matches_documented_reference_case(case):
    model = UnboundedKnapsackModel.from_parts(
        tuple(
            UnboundedKnapsackItem(item["name"], item["value"], item["weight"])
            for item in case["items"]
        ),
        capacity=case["capacity"],
    )

    solution = SolveUnboundedKnapsackUseCase(UnboundedKnapsackSolverAdapter()).execute(model)

    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(case["expected_objective"])
    assert solution.quantities == tuple(case["expected_quantities"])
    assert solution.total_weight <= model.capacity
