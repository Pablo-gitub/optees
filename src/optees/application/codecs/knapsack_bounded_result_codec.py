from __future__ import annotations

from optees.application.codecs.knapsack_result_helpers import (
    diagnostics_payload,
    integer_quantity_result_payload,
    mathematical_status,
    not_solved_warning,
)
from optees.application.contracts.capability_ids import (
    KNAPSACK_BOUNDED_CAPABILITY_ID,
)
from optees.application.contracts.execution import SerializedResult
from optees.domain.entities.knapsack.bounded_solution import BoundedKnapsackSolution


class KnapsackBoundedResultCodec:
    capability_id = KNAPSACK_BOUNDED_CAPABILITY_ID
    result_schema_version = "1"

    def serialize(self, solution: BoundedKnapsackSolution) -> SerializedResult:
        return SerializedResult(
            mathematical_status=mathematical_status(solution.status),
            result=integer_quantity_result_payload(solution),
            diagnostics=diagnostics_payload(solution.diagnostics, solution.extras),
            warnings=not_solved_warning(
                solution.status,
                solver_label="exact bounded dynamic-programming solver",
            ),
        )
