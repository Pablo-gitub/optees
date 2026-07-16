from __future__ import annotations

from optees.application.codecs.knapsack_result_helpers import (
    finite,
    mathematical_status,
    not_solved_warning,
    optional_finite,
)
from optees.application.contracts.execution import SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.knapsack.fractional_solution import (
    FractionalKnapsackSolution,
)


class KnapsackFractionalResultCodec:
    capability_id = "knapsack.fractional"
    result_schema_version = "1"

    def serialize(self, solution: FractionalKnapsackSolution) -> SerializedResult:
        selected_items = [
            {
                "index": index,
                "name": name,
                "fraction": finite(solution.fractions[index], "fraction"),
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
                "fractions": [
                    finite(fraction, f"fractions[{index}]")
                    for index, fraction in enumerate(solution.fractions)
                ],
                "selected_indices": list(solution.selected_indices),
                "selected_items": selected_items,
                "total_value": finite(solution.total_value, "total_value"),
                "total_weight": finite(solution.total_weight, "total_weight"),
                "remaining_capacity": optional_finite(
                    solution.remaining_capacity,
                    "remaining_capacity",
                ),
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "method": solution.diagnostics.method,
                "message": solution.diagnostics.message,
                "item_count": solution.diagnostics.item_count,
                "capacity": _optional_extra_number(solution.extras, "capacity"),
                "max_items": _optional_extra_integer(solution.extras, "max_items"),
                "complexity": solution.diagnostics.complexity,
                "success": _optional_extra_bool(solution.extras, "success"),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=mathematical_status(solution.status),
            result=result,
            diagnostics=diagnostics,
            warnings=not_solved_warning(
                solution.status,
                solver_label="exact fractional greedy solver",
            ),
        )


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized


def _optional_extra_number(extras: dict[str, object], key: str) -> float | None:
    value = extras.get(key)
    return None if value is None else finite(value, key)


def _optional_extra_integer(extras: dict[str, object], key: str) -> int | None:
    value = extras.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_extra_bool(extras: dict[str, object], key: str) -> bool | None:
    value = extras.get(key)
    return value if isinstance(value, bool) else None
