from __future__ import annotations

import math

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.json_value import JsonValue, require_json_value
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.value_objects.nlp.solve_status import NLPSolveStatus


class NLPResultCodec:
    capability_id = "nlp.continuous_local"
    result_schema_version = "1"

    def serialize(self, solution: NLPSolution) -> SerializedResult:
        mathematical_status = _mathematical_status(solution)
        result = _strict_payload(
            {
                "objective": solution.objective,
                "variables": [
                    {"name": name, "value": value}
                    for name, value in solution.values.items()
                ],
                "local_candidate": mathematical_status
                is MathematicalStatus.FEASIBLE,
            },
            path="$.result",
        )
        diagnostics = _strict_payload(
            {
                "solver_status": solution.status.value,
                "method": _optional_string(solution.extras.get("method")),
                "success": _optional_bool(solution.extras.get("success")),
                "message": solution.termination_message,
                "iterations": solution.iterations,
                "evaluations": solution.evaluations,
                "scipy_status": _optional_integer(
                    solution.extras.get("scipy_status")
                ),
                "convergence_history": list(solution.convergence_history),
            },
            path="$.diagnostics",
        )
        return SerializedResult(
            mathematical_status=mathematical_status,
            result=result,
            diagnostics=diagnostics,
            warnings=_warnings(solution),
        )


def _mathematical_status(solution: NLPSolution) -> MathematicalStatus:
    if solution.status in {
        NLPSolveStatus.CONVERGED,
        NLPSolveStatus.ITERATION_LIMIT,
    } and solution.objective is not None and solution.values:
        return MathematicalStatus.FEASIBLE
    return MathematicalStatus.NOT_SOLVED


def _warnings(solution: NLPSolution) -> tuple[str, ...]:
    if solution.status is NLPSolveStatus.CONVERGED:
        return (
            "The result is a local numerical candidate, not a certificate of "
            "global optimality.",
        )
    if solution.status is NLPSolveStatus.ITERATION_LIMIT:
        return (
            "The iteration limit was reached; the returned local candidate has "
            "no convergence or global-optimality certificate.",
        )
    return ("The nonlinear solver produced no usable local candidate.",)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_integer(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if math.isfinite(numeric) and numeric == normalized else None


def _strict_payload(payload: dict[str, object], *, path: str) -> dict[str, JsonValue]:
    normalized = require_json_value(payload, path=path)
    assert isinstance(normalized, dict)
    return normalized
