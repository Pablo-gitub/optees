from __future__ import annotations

from optees.application.codecs.knapsack_result_helpers import (
    finite,
    mathematical_status,
    not_solved_warning,
    optional_finite,
)
from optees.application.contracts.capability_ids import (
    KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
)
from optees.application.contracts.execution import SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.application.usecases.solve_multi_dimensional_knapsack_capability_usecase import (
    MultiDimensionalResult,
)
from optees.domain.entities.knapsack.multi_dimensional_quantity_solution import (
    MultiDimensionalQuantityKnapsackSolution,
)


class KnapsackMultiDimensionalResultCodec:
    capability_id = KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: MultiDimensionalResult) -> SerializedResult:
        quantities = _quantities(solution)
        selected_items = [
            {
                "index": index,
                "name": name,
                "quantity": finite(quantities[index], "quantity"),
            }
            for index, name in zip(
                solution.selected_indices,
                solution.selected_item_names,
                strict=True,
            )
        ]
        result = _strict_payload(
            {
                "objective": optional_finite(solution.objective, "objective"),
                "quantities": [
                    finite(quantity, f"quantities[{index}]")
                    for index, quantity in enumerate(quantities)
                ],
                "selected_indices": list(solution.selected_indices),
                "selected_items": selected_items,
                "total_value": finite(solution.total_value, "total_value"),
                "resources": _resource_results(solution),
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "method": solution.diagnostics.method,
                "message": solution.diagnostics.message,
                "item_count": solution.diagnostics.item_count,
                "resource_count": solution.extras.get("resource_count"),
                "max_items": solution.extras.get("max_items"),
                "complexity": solution.diagnostics.complexity,
                "domain": solution.extras.get("multi_domain", "zero_one"),
                "success": solution.extras.get("success"),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=mathematical_status(solution.status),
            result=result,
            diagnostics=diagnostics,
            warnings=not_solved_warning(
                solution.status,
                solver_label="multi-dimensional knapsack solver",
            ),
        )


def _quantities(solution: MultiDimensionalResult) -> tuple[float, ...]:
    if isinstance(solution, MultiDimensionalQuantityKnapsackSolution):
        return solution.quantities
    selected = set(solution.selected_indices)
    item_count = int(solution.extras.get("item_count") or 0)
    if item_count <= 0:
        item_count = max(selected, default=-1) + 1
    return tuple(1.0 if index in selected else 0.0 for index in range(item_count))


def _resource_results(solution: MultiDimensionalResult) -> list[dict[str, object]]:
    names = list(solution.extras.get("resource_names") or [])
    capacities = list(solution.extras.get("capacities") or [])
    count = len(solution.resource_usage_totals)
    return [
        {
            "index": index,
            "name": str(names[index]) if index < len(names) else f"Resource {index + 1}",
            "capacity": finite(capacities[index], "capacity")
            if index < len(capacities)
            else finite(
                solution.resource_usage_totals[index]
                + solution.remaining_capacities[index],
                "capacity",
            ),
            "used": finite(solution.resource_usage_totals[index], "used"),
            "remaining": finite(solution.remaining_capacities[index], "remaining"),
        }
        for index in range(count)
    ]


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
