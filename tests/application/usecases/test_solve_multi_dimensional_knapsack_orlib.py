from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.usecases.solve_multi_dimensional_knapsack_usecase import (
    SolveMultiDimensionalKnapsackUseCase,
)
from optees.data.adapters.knapsack.multi_dimensional_knapsack_solver_adapter import (
    MultiDimensionalKnapsackSolverAdapter,
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
from optees.utility.data_adapters.orlib_mknap_adapter import load_orlib_mknap


DATASET = Path("tests/data/knapsack/orlib/mknap1.txt")


def _model_from_orlib(instance_index: int) -> tuple[MultiDimensionalKnapsackModel, float]:
    data = load_orlib_mknap(DATASET, instance_index)
    resources = tuple(
        MultiDimensionalKnapsackResource(f"Resource {index + 1}", capacity)
        for index, capacity in enumerate(data["capacities"])
    )
    items = tuple(
        MultiDimensionalKnapsackItem(
            f"mknap1_{instance_index}_item_{item_index + 1}",
            value,
            data["usage_matrix"][item_index],
        )
        for item_index, value in enumerate(data["values"])
    )
    return MultiDimensionalKnapsackModel.from_parts(resources, items), data["known_optimum"]


@pytest.mark.parametrize("instance_index", [1, 2, 3])
def test_solver_matches_orlib_known_optimum_for_small_mknap_instances(instance_index):
    model, known_optimum = _model_from_orlib(instance_index)

    solution = SolveMultiDimensionalKnapsackUseCase(
        MultiDimensionalKnapsackSolverAdapter()
    ).execute(model)

    assert solution.status is KnapsackSolveStatus.OPTIMAL
    assert solution.objective == pytest.approx(known_optimum)
    assert solution.total_value == pytest.approx(known_optimum)
    assert all(remaining >= 0 for remaining in solution.remaining_capacities)
