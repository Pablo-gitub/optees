from __future__ import annotations

from optees.application.contracts.execution import SerializedResult
from optees.application.contracts.json_value import require_json_value
from optees.application.codecs.knapsack_result_helpers import (
    diagnostics_payload,
    finite,
    mathematical_status,
    not_solved_warning,
    optional_finite,
)
from optees.application.contracts.capability_ids import (
    KNAPSACK_ZERO_ONE_CAPABILITY_ID,
)
from optees.domain.entities.knapsack.solution import KnapsackSolution


class KnapsackZeroOneResultCodec:
    capability_id = KNAPSACK_ZERO_ONE_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: KnapsackSolution) -> SerializedResult:
        selected_items = [
            {"index": index, "name": name}
            for index, name in zip(
                solution.selected_indices,
                solution.selected_item_names,
                strict=True,
            )
        ]
        result: dict[str, object] = {
            "objective": optional_finite(solution.objective, "objective"),
            "selected_indices": list(solution.selected_indices),
            "selected_items": selected_items,
            "total_value": finite(solution.total_value, "total_value"),
            "total_weight": solution.total_weight,
            "remaining_capacity": solution.remaining_capacity,
        }
        normalized_result = require_json_value(result, path="$.result")
        assert isinstance(normalized_result, dict)
        return SerializedResult(
            mathematical_status=mathematical_status(solution.status),
            result=normalized_result,
            diagnostics=diagnostics_payload(solution.diagnostics, solution.extras),
            warnings=not_solved_warning(
                solution.status,
                solver_label="exact dynamic-programming solver",
            ),
        )
